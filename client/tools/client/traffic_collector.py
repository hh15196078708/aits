# -*- coding: utf-8 -*-
"""
模块名称: traffic_collector.py
模块功能: 流量采集与攻击检测协调器
依赖模块:
    - port_scan_detector: 端口扫描检测
    - web_attack_detector: Web应用攻击检测
    - network_client: 攻击日志上报
    - constants: 配置常量
系统适配: 所有平台通用

说明:
    本模块作为攻击检测的统一入口，协调各检测子模块的生命周期，
    并负责将检测到的攻击事件批量上报至服务端。

    当前已集成的检测模块:
        - 端口扫描检测 (port_scan_detector)
        - Web攻击检测 (web_attack_detector)
          支持: SQL注入、XSS、目录遍历、命令注入、CSRF、远程代码执行

    上报流程:
        1. 各检测器将事件存入各自的待上报队列
        2. 本模块的上报线程定期调用 get_recent_events() 取出事件
        3. 批量打包后通过 network_client 对应接口发送至服务端
        4. 上报失败的事件会在下次尝试时合并重传（最多保留 MAX_PENDING）
"""

import time
import threading
from typing import List, Dict, Optional

from config_manager import config_manager
from constants import (
    ATTACK_LOG_BATCH_SIZE,
    ATTACK_LOG_UPLOAD_INTERVAL,
    ATTACK_LOG_UPLOAD_ENDPOINT,
    ATTACK_LOG_WEB_UPLOAD_ENDPOINT,
)
from port_scan_detector import port_scan_detector, PortScanEvent
from web_attack_detector import web_attack_detector, WebAttackEvent
from logger import logger


# 待上报事件的最大缓存数量，防止内存无限增长
_MAX_PENDING_EVENTS = 500


class TrafficCollector:
    """
    流量采集与攻击检测协调器（单例）

    职责:
        1. 启动/停止各攻击检测模块
        2. 收集检测事件并批量上报至服务端
        3. 提供统一的状态查询接口

    线程模型:
        - UploadThread: 定期将检测事件上报至服务端（守护线程）
        - 各检测器内部维护自己的检测线程
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if TrafficCollector._initialized:
            return

        self._running = False
        self._stop_event = threading.Event()
        self._upload_thread: Optional[threading.Thread] = None

        # 端口扫描事件重试缓冲
        self._retry_buffer: List[dict] = []
        self._retry_lock = threading.Lock()

        # Web攻击事件重试缓冲
        self._web_retry_buffer: List[dict] = []
        self._web_retry_lock = threading.Lock()

        TrafficCollector._initialized = True

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, object]:
        """
        启动流量采集与攻击检测。

        返回各子模块启动状态的汇总字典，例如:
            {
                "port_scan": {"connection": True, "packet": False, "log": True},
                "upload": True
            }
        """
        if self._running:
            return self.get_status()

        self._running = True
        self._stop_event.clear()

        status: Dict[str, object] = {}

        # 启动端口扫描检测器
        ps_status = port_scan_detector.start()
        status["port_scan"] = ps_status

        # 启动Web攻击检测器
        wa_status = web_attack_detector.start()
        status["web_attack"] = wa_status

        # 启动事件上报线程
        self._upload_thread = threading.Thread(
            target=self._upload_loop,
            name="AttackLogUploadThread",
            daemon=True,
        )
        self._upload_thread.start()
        status["upload"] = True

        logger.info("流量采集与攻击检测已启动（端口扫描 + Web攻击检测）")
        return status

    def stop(self):
        """停止所有检测模块和上报线程"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        # 停止端口扫描检测
        port_scan_detector.stop()

        # 停止Web攻击检测
        web_attack_detector.stop()

        # 等待上报线程结束
        if self._upload_thread and self._upload_thread.is_alive():
            self._upload_thread.join(timeout=5)

        logger.info("流量采集已停止")

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """返回当前运行状态"""
        with self._retry_lock:
            retry_count = len(self._retry_buffer)
        with self._web_retry_lock:
            web_retry_count = len(self._web_retry_buffer)
        return {
            "running":                self._running,
            "port_scan":              port_scan_detector.get_status(),
            "web_attack":             web_attack_detector.get_status(),
            "retry_buffer_size":      retry_count,
            "web_retry_buffer_size":  web_retry_count,
        }

    # ------------------------------------------------------------------
    # 内部：事件上报循环
    # ------------------------------------------------------------------

    def _upload_loop(self):
        """
        定期将攻击事件上报至服务端。

        每隔 ATTACK_LOG_UPLOAD_INTERVAL 秒执行一次：
        1. 从各检测器取出待上报事件
        2. 合并上次失败的重试缓冲
        3. 按 ATTACK_LOG_BATCH_SIZE 分批上报
        4. 上报失败则存入重试缓冲（下次尝试）
        """
        while not self._stop_event.is_set():
            try:
                self._do_upload()
                self._do_web_upload()
            except Exception as e:
                logger.error(f"攻击日志上报循环异常: {e}")

            self._stop_event.wait(ATTACK_LOG_UPLOAD_INTERVAL)

    def _do_upload(self):
        """执行一次端口扫描事件上报"""
        new_events: List[dict] = []
        new_events.extend(
            port_scan_detector.get_recent_events(max_count=ATTACK_LOG_BATCH_SIZE)
        )

        if not new_events:
            with self._retry_lock:
                if not self._retry_buffer:
                    return
                to_send = self._retry_buffer[:ATTACK_LOG_BATCH_SIZE]
                self._retry_buffer = self._retry_buffer[ATTACK_LOG_BATCH_SIZE:]
        else:
            with self._retry_lock:
                combined = self._retry_buffer + new_events
                self._retry_buffer = []
            to_send = combined[:ATTACK_LOG_BATCH_SIZE]
            overflow = combined[ATTACK_LOG_BATCH_SIZE:]
            if overflow:
                with self._retry_lock:
                    self._retry_buffer = overflow + self._retry_buffer

        if not to_send:
            return

        success = self._upload_batch(to_send)
        if not success:
            with self._retry_lock:
                self._retry_buffer = to_send + self._retry_buffer
                if len(self._retry_buffer) > _MAX_PENDING_EVENTS:
                    dropped = len(self._retry_buffer) - _MAX_PENDING_EVENTS
                    self._retry_buffer = self._retry_buffer[-_MAX_PENDING_EVENTS:]
                    logger.warning(f"端口扫描重试缓冲已满，丢弃 {dropped} 条日志")

    def _do_web_upload(self):
        """执行一次Web攻击事件上报"""
        new_events: List[dict] = []
        new_events.extend(
            web_attack_detector.get_recent_events(max_count=ATTACK_LOG_BATCH_SIZE)
        )

        if not new_events:
            with self._web_retry_lock:
                if not self._web_retry_buffer:
                    return
                to_send = self._web_retry_buffer[:ATTACK_LOG_BATCH_SIZE]
                self._web_retry_buffer = self._web_retry_buffer[ATTACK_LOG_BATCH_SIZE:]
        else:
            with self._web_retry_lock:
                combined = self._web_retry_buffer + new_events
                self._web_retry_buffer = []
            to_send = combined[:ATTACK_LOG_BATCH_SIZE]
            overflow = combined[ATTACK_LOG_BATCH_SIZE:]
            if overflow:
                with self._web_retry_lock:
                    self._web_retry_buffer = overflow + self._web_retry_buffer

        if not to_send:
            return

        success = self._upload_web_batch(to_send)
        if not success:
            with self._web_retry_lock:
                self._web_retry_buffer = to_send + self._web_retry_buffer
                if len(self._web_retry_buffer) > _MAX_PENDING_EVENTS:
                    dropped = len(self._web_retry_buffer) - _MAX_PENDING_EVENTS
                    self._web_retry_buffer = self._web_retry_buffer[-_MAX_PENDING_EVENTS:]
                    logger.warning(f"Web攻击重试缓冲已满，丢弃 {dropped} 条日志")

    def _upload_batch(self, events: List[dict]) -> bool:
        """
        将一批端口扫描事件上报至服务端。

        返回 True 表示上报成功（或服务端明确接收），False 表示失败需重试。
        """
        if not events:
            return True

        try:
            client_id = config_manager.get_client_id()
            from network_client import network_client
            success, error = network_client.upload_attack_logs(client_id, events)
            if success:
                logger.info(f"端口扫描日志上报成功，共 {len(events)} 条")
                return True
            else:
                logger.warning(f"端口扫描日志上报失败: {error}，将在下次重试")
                return False
        except Exception as e:
            logger.error(f"端口扫描日志上报异常: {e}")
            return False

    def _upload_web_batch(self, events: List[dict]) -> bool:
        """
        将一批Web攻击事件上报至服务端。

        返回 True 表示上报成功（或服务端明确接收），False 表示失败需重试。
        """
        if not events:
            return True

        try:
            client_id = config_manager.get_client_id()
            from network_client import network_client
            success, error = network_client.upload_web_attack_logs(client_id, events)
            if success:
                logger.info(f"Web攻击日志上报成功，共 {len(events)} 条")
                return True
            else:
                logger.warning(f"Web攻击日志上报失败: {error}，将在下次重试")
                return False
        except Exception as e:
            logger.error(f"Web攻击日志上报异常: {e}")
            return False


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

traffic_collector = TrafficCollector()
