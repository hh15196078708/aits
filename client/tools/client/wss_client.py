# -*- coding: utf-8 -*-
"""
模块名称: wss_client.py
模块功能: WebSocket Secure (WSS) 长连接客户端
依赖模块:
    - 第三方库: websocket-client>=1.6.0 (pip install websocket-client)
    - 本地模块: constants, config_manager, hardware_collector, auth_manager, ip_blocker, logger
系统适配: 所有平台通用

说明:
    本模块在客户端注册完成后建立与服务端的 WSS 持久连接，替代原有的 HTTP 轮询心跳：
    1. 注册成功后立即连接 WSS 端点
    2. 连接建立后定时通过 WSS 发送心跳（含硬件状态数据）
    3. 接收并处理服务端下发的四类指令：
        - auto_block  : 开启/关闭自动IP拉黑
        - block_ip    : 封禁指定IP
        - whitelist   : 更新IP白名单
        - shutdown    : 关闭客户端程序（并执行系统关机）
    4. 断线后自动重连（可配置间隔）

服务端消息格式（JSON）：
    心跳确认:  {"type": "heartbeat_ack", "authStatus": "normal|expired", "safeStatus": "ON|OFF"}
    自动拉黑:  {"type": "auto_block", "enabled": true|false}
    封禁IP:    {"type": "block_ip", "ip": "1.2.3.4"}
    白名单:    {"type": "whitelist", "ips": ["1.2.3.4", "10.0.0.0/8", ...]}
    关机:      {"type": "shutdown"}

客户端心跳消息格式（JSON）：
    {
        "type":            "heartbeat",
        "id":              "<client_id>",
        "projectId":       "<project_id>",
        "safeCode":        "<machine_code>",
        "safeSecret":      "<auth_key>",
        "safeStatus":      "ON",
        "safeOs":          {...},
        "safeCpu":         {...},
        "safeCpuUsage":    5.2,
        "safeMemory":      16.0,
        "safeMemoryUsage": 45.3,
        "safeDisk":        500.0,
        "safeDiskUsage":   67.8
    }
"""

import json
import platform
import ssl
import subprocess
import threading
from typing import Callable, Optional

# 尝试导入 websocket-client 库
try:
    import websocket  # websocket-client 包
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

from auth_manager import auth_manager
from config_manager import config_manager
from constants import (
    AUTH_STATUS_EXPIRED,
    AUTH_STATUS_NORMAL,
    HEARTBEAT_INTERVAL,
    PROJECT_ID,
    WSS_BASE_URL,
    WSS_RECONNECT_INTERVAL,
    WSS_SSL_VERIFY,
)
from hardware_collector import hardware_collector
from logger import logger
from utils import format_datetime


class WSSClient:
    """
    WSS WebSocket 长连接客户端（单例）

    功能:
        - 注册完成后建立 WSS 持久连接
        - 通过 WSS 定时发送心跳（替代 HTTP 轮询）
        - 接收并处理服务端下发的四类控制指令
        - 断线自动重连

    生命周期:
        start() → 连接循环（自动重连）→ stop()
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if WSSClient._initialized:
            return

        self._ws: Optional["websocket.WebSocketApp"] = None
        self._connected: bool = False
        self._stop_event = threading.Event()
        self._ws_thread: Optional[threading.Thread] = None
        self._heartbeat_timer: Optional[threading.Timer] = None

        # 客户端身份信息（start() 时传入）
        self._client_id: str = ""
        self._machine_code: str = ""
        self._auth_key: str = ""

        # 回调函数
        self._on_auth_expired: Optional[Callable] = None
        self._on_shutdown: Optional[Callable] = None

        WSSClient._initialized = True

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """当前是否已建立 WSS 连接"""
        return self._connected

    @property
    def available(self) -> bool:
        """websocket-client 库是否可用"""
        return WEBSOCKET_AVAILABLE

    def start(self, client_id: str, machine_code: str, auth_key: str,
              on_auth_expired: Optional[Callable] = None,
              on_shutdown: Optional[Callable] = None) -> bool:
        """
        启动 WSS 客户端

        功能: 保存身份信息，启动后台连接线程（含自动重连逻辑）
        参数:
            client_id:       服务端分配的客户端ID
            machine_code:    本机唯一机器码
            auth_key:        授权密钥
            on_auth_expired: 授权到期时的回调（无参数）
            on_shutdown:     收到关机指令时的回调（无参数）
        返回值:
            True  = 启动成功
            False = websocket-client 未安装
        """
        if not WEBSOCKET_AVAILABLE:
            logger.error(
                "websocket-client 未安装，无法启动 WSS 连接。"
                "请执行: pip install websocket-client>=1.6.0"
            )
            return False

        self._client_id = client_id
        self._machine_code = machine_code
        self._auth_key = auth_key
        self._on_auth_expired = on_auth_expired
        self._on_shutdown = on_shutdown

        self._stop_event.clear()
        self._ws_thread = threading.Thread(
            target=self._run_loop,
            name="WSSClientThread",
            daemon=True
        )
        self._ws_thread.start()
        logger.info(f"WSS客户端已启动，连接地址: {WSS_BASE_URL}/{client_id}")
        return True

    def stop(self) -> None:
        """
        停止 WSS 客户端

        功能: 取消心跳定时器，关闭 WSS 连接，等待线程退出
        """
        self._stop_event.set()
        self._cancel_heartbeat_timer()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=3)
        logger.info("WSS客户端已停止")

    # ------------------------------------------------------------------
    # 连接循环（自动重连）
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """
        WSS 连接主循环

        功能: 不断尝试建立连接，断线后等待 WSS_RECONNECT_INTERVAL 秒后重连
        """
        while not self._stop_event.is_set():
            try:
                self._connect_once()
            except Exception as e:
                logger.error(f"WSS连接异常: {e}")

            if not self._stop_event.is_set():
                logger.info(
                    f"WSS连接断开，{WSS_RECONNECT_INTERVAL}秒后尝试重连... "
                    f"（目标: {WSS_BASE_URL}/{self._client_id}）"
                )
                auth_manager.start_offline_timer()
                self._stop_event.wait(WSS_RECONNECT_INTERVAL)

    def _connect_once(self) -> None:
        """
        建立单次 WSS 连接

        功能: 将 client_id 拼接到 WSS_BASE_URL 末尾，创建 WebSocketApp 并调用 run_forever()（阻塞直到断开）
        连接 URL 格式: {WSS_BASE_URL}/{client_id}
        """
        connect_url = f"{WSS_BASE_URL}/{self._client_id}"
        ws = websocket.WebSocketApp(
            connect_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._ws = ws

        # SSL 配置
        sslopt: dict = {}
        if not WSS_SSL_VERIFY:
            sslopt = {"cert_reqs": ssl.CERT_NONE}

        # run_forever 阻塞直到连接断开
        ws.run_forever(sslopt=sslopt, ping_interval=30, ping_timeout=10)

    # ------------------------------------------------------------------
    # WebSocketApp 回调
    # ------------------------------------------------------------------

    def _on_open(self, ws) -> None:
        """连接建立回调：立即发送心跳并启动定时器"""
        self._connected = True
        logger.info("WSS连接已建立")
        self._send_heartbeat()
        self._schedule_heartbeat()

    def _on_message(self, ws, message: str) -> None:
        """接收服务端消息回调：解析 JSON 并分发到对应处理函数"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "heartbeat_ack":
                self._handle_heartbeat_ack(data)
            elif msg_type == "auto_block":
                self._handle_auto_block(data)
            elif msg_type == "block_ip":
                self._handle_block_ip(data)
            elif msg_type == "whitelist":
                self._handle_whitelist(data)
            elif msg_type == "shutdown":
                self._handle_shutdown()
            else:
                logger.debug(f"收到未知类型WSS消息: {msg_type}")

        except json.JSONDecodeError:
            logger.warning(f"WSS消息JSON解析失败: {message[:200]}")
        except Exception as e:
            logger.error(f"处理WSS消息异常: {e}")

    def _on_error(self, ws, error) -> None:
        """连接错误回调"""
        logger.warning(f"WSS连接错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """连接关闭回调：取消心跳定时器，启动离线计时器"""
        self._connected = False
        self._cancel_heartbeat_timer()
        logger.info(f"WSS连接已关闭 (code={close_status_code}, msg={close_msg})")

    # ------------------------------------------------------------------
    # 心跳
    # ------------------------------------------------------------------

    def _schedule_heartbeat(self) -> None:
        """调度下一次心跳定时器"""
        self._cancel_heartbeat_timer()
        if not self._stop_event.is_set() and self._connected:
            self._heartbeat_timer = threading.Timer(
                HEARTBEAT_INTERVAL,
                self._heartbeat_tick
            )
            self._heartbeat_timer.daemon = True
            self._heartbeat_timer.start()

    def _heartbeat_tick(self) -> None:
        """心跳定时触发：发送心跳并重新调度"""
        if not self._stop_event.is_set() and self._connected:
            self._send_heartbeat()
            self._schedule_heartbeat()

    def _cancel_heartbeat_timer(self) -> None:
        """取消心跳定时器"""
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
            self._heartbeat_timer = None

    def _send_heartbeat(self) -> None:
        """
        发送心跳消息

        功能: 采集硬件数据，构建心跳消息，通过 WSS 发送
        """
        if not self._ws or not self._connected:
            return
        try:
            heartbeat_data = hardware_collector.collect_all()
            message = {
                "type":            "heartbeat",
                "id":              self._client_id,
                "projectId":       PROJECT_ID,
                "safeCode":        self._machine_code,
                "safeSecret":      self._auth_key,
                "safeStatus":      "ON",
                "safeOs":          heartbeat_data.get("os_info", {}),
                "safeCpu":         heartbeat_data.get("cpu_config", {}),
                "safeCpuUsage":    heartbeat_data.get("cpu_usage", 0.0),
                "safeMemory":      heartbeat_data.get("memory_size", 0.0),
                "safeMemoryUsage": heartbeat_data.get("memory_usage", 0.0),
                "safeDisk":        heartbeat_data.get("disk_size", 0.0),
                "safeDiskUsage":   heartbeat_data.get("disk_usage", 0.0),
            }
            self._ws.send(json.dumps(message, ensure_ascii=False))
            logger.debug("WSS心跳已发送")
        except Exception as e:
            logger.error(f"发送WSS心跳失败: {e}")

    # ------------------------------------------------------------------
    # 指令处理
    # ------------------------------------------------------------------

    def _handle_heartbeat_ack(self, data: dict) -> None:
        """
        处理服务端心跳确认

        功能: 更新授权状态，重置离线计时器，记录心跳时间
        消息字段:
            authStatus: "normal" | "expired"
            safeStatus: "ON" | "OFF"
        """
        auth_status = data.get("authStatus", AUTH_STATUS_NORMAL)
        safe_status = data.get("safeStatus", "ON")

        auth_manager.update_auth_status(auth_status)
        auth_manager.reset_offline_timer()
        config_manager.set_last_heartbeat_time()

        if safe_status == "OFF" or auth_status == AUTH_STATUS_EXPIRED:
            logger.warning("服务端返回授权已到期")
            auth_manager.handle_auth_expired()
            if self._on_auth_expired:
                self._on_auth_expired()
        else:
            logger.info(f"WSS心跳成功 [{format_datetime()}]")

    def _handle_auto_block(self, data: dict) -> None:
        """
        处理自动拉黑开关指令

        功能: 根据服务端指令开启或关闭IP自动拉黑功能
        消息字段:
            enabled: true | false
        """
        enabled = bool(data.get("enabled", False))
        from ip_blocker import ip_blocker
        ip_blocker.set_enabled(enabled)
        logger.info(f"收到服务端指令: 自动拉黑功能{'开启' if enabled else '关闭'}")

    def _handle_block_ip(self, data: dict) -> None:
        """
        处理封禁指定IP指令

        功能: 强制封禁服务端指定的IP地址
        消息字段:
            ip: "1.2.3.4"
        """
        ip = str(data.get("ip", "")).strip()
        if not ip:
            logger.warning("收到block_ip指令但IP字段为空，已忽略")
            return
        from ip_blocker import ip_blocker
        success = ip_blocker.force_block_ip(ip)
        logger.info(
            f"收到服务端指令: 封禁IP {ip}，"
            f"结果: {'成功' if success else '失败（见上方日志）'}"
        )

    def _handle_whitelist(self, data: dict) -> None:
        """
        处理IP白名单更新指令

        功能: 替换本地IP白名单，自动解封已在白名单中的已封禁IP
        消息字段:
            ips: ["1.2.3.4", "10.0.0.0/8", ...]
        """
        ips = data.get("ips", [])
        if not isinstance(ips, list):
            ips = []
        from ip_blocker import ip_blocker
        ip_blocker.update_whitelist(ips)
        logger.info(f"收到服务端指令: 更新IP白名单，共{len(ips)}条")

    def _handle_shutdown(self) -> None:
        """
        处理关机指令

        功能:
            1. 触发客户端程序退出回调
            2. 执行操作系统级关机（Windows: shutdown /s /f /t 5，Linux/macOS: shutdown -h +0）
        """
        logger.info("收到服务端关机指令，准备执行系统关机...")

        # 先通知主程序优雅退出
        if self._on_shutdown:
            self._on_shutdown()

        # 执行系统级关机
        try:
            sys_platform = platform.system()
            if sys_platform == "Windows":
                # /s=关机 /f=强制关闭应用 /t 5=5秒后执行
                subprocess.Popen(
                    ["shutdown", "/s", "/f", "/t", "5"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info("系统关机指令已下发（5秒后执行）")
            else:
                # Linux / macOS
                subprocess.Popen(
                    ["shutdown", "-h", "+0"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info("系统关机指令已下发")
        except Exception as e:
            logger.error(f"执行系统关机失败: {e}")


# 全局单例
wss_client = WSSClient()
