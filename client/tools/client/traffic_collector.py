# -*- coding: utf-8 -*-
"""
模块名称: traffic_collector.py
模块功能: 流量采集与攻击检测协调器
依赖模块:
    - port_scan_detector: 端口扫描检测
    - web_attack_detector: Web应用攻击检测
    - payload_sniffer: Payload流量检测
    - process_monitor: 进程监控检测
    - network_client: 攻击日志上报
    - ip_blocker: IP自动封禁
    - constants: 配置常量
系统适配: 所有平台通用

上报架构（统一）:
    所有检测模块（端口扫描 / Web日志 / Payload抓包 / 进程监控）的事件
    汇入同一个重试缓冲，由单一上报循环定期通过 network_client.upload_attack_logs()
    批量发送至统一接口。

IP封禁策略:
    开启 ip_blocker 后，任意模块检测到的攻击事件都会立即触发 IP 封禁，
    不受上报结果影响，确保防御响应零延迟。
"""

import time
import threading
from typing import List, Dict, Optional

from config_manager import config_manager
from constants import (
    ATTACK_LOG_BATCH_SIZE,
    ATTACK_LOG_UPLOAD_INTERVAL,
)
from port_scan_detector import port_scan_detector
from web_attack_detector import web_attack_detector
from payload_sniffer import payload_sniffer
from ip_blocker import ip_blocker
from process_monitor import process_monitor
from logger import logger


# 待上报事件的最大缓存数量，防止内存无限增长
_MAX_PENDING_EVENTS = 500


class TrafficCollector:
    """
    流量采集与攻击检测协调器（单例）

    职责:
        1. 启动/停止各攻击检测模块
        2. 统一收集所有检测事件，归一化后批量上报至服务端
        3. 对所有攻击来源 IP 执行自动封禁（开启 ip_blocker 时）
        4. 提供统一的状态查询接口

    线程模型:
        - AttackLogUploadThread: 定期将所有检测事件上报至服务端（守护线程）
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

        # 统一重试缓冲（所有攻击类型共用）
        self._retry_buffer: List[dict] = []
        self._retry_lock = threading.Lock()

        TrafficCollector._initialized = True

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, object]:
        """
        启动流量采集与攻击检测。

        返回各子模块启动状态的汇总字典，例如:
            {
                "port_scan":     {"connection": True, "packet": False, "log": True},
                "web_attack":    {"log": True},
                "payload_sniffer": {"enabled": True, "running": True, ...},
                "ip_blocker":    True,
                "process_monitor": True,
                "upload":        True
            }
        """
        if self._running:
            return self.get_status()

        self._running = True
        self._stop_event.clear()

        status: Dict[str, object] = {}

        # 启动端口扫描检测器
        status["port_scan"] = port_scan_detector.start()

        # 启动Web攻击检测器
        status["web_attack"] = web_attack_detector.start()

        # 启动Payload流量嗅探器
        status["payload_sniffer"] = payload_sniffer.start()

        # 启动IP拉黑管理器
        status["ip_blocker"] = ip_blocker.start()

        # 启动进程监控器
        status["process_monitor"] = process_monitor.start()

        # 启动统一上报线程
        self._upload_thread = threading.Thread(
            target=self._upload_loop,
            name="AttackLogUploadThread",
            daemon=True,
        )
        self._upload_thread.start()
        status["upload"] = True

        logger.info(
            "流量采集与攻击检测已启动（端口扫描 / Web攻击 / Payload嗅探 / 进程监控），"
            f"统一上报间隔: {ATTACK_LOG_UPLOAD_INTERVAL}秒"
        )
        return status

    def stop(self):
        """停止所有检测模块和上报线程"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        port_scan_detector.stop()
        web_attack_detector.stop()
        payload_sniffer.stop()
        ip_blocker.stop()
        process_monitor.stop()

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
        return {
            "running":          self._running,
            "port_scan":        port_scan_detector.get_status(),
            "web_attack":       web_attack_detector.get_status(),
            "payload_sniffer":  payload_sniffer.get_status(),
            "ip_blocker":       ip_blocker.get_status(),
            "process_monitor":  process_monitor.get_status(),
            "retry_buffer_size": retry_count,
        }

    # ------------------------------------------------------------------
    # 内部：IP 封禁（所有攻击类型统一处理）
    # ------------------------------------------------------------------

    def _block_attack_ips(self, events: List[dict]) -> None:
        """
        对所有攻击事件的来源 IP 执行防火墙封禁。

        无论攻击类型（端口扫描/Web攻击/Payload/进程监控），只要有有效的
        source_ip 且 ip_blocker 已启用，立即触发封禁，不等待上报结果。
        """
        if not ip_blocker.enabled:
            return
        for event in events:
            source_ip = event.get("source_ip", "")
            if source_ip:
                ip_blocker.maybe_block_ip(
                    source_ip,
                    event.get("attack_type", ""),
                    event.get("level", "low"),
                )

    # ------------------------------------------------------------------
    # 内部：统一上报循环
    # ------------------------------------------------------------------

    def _upload_loop(self):
        """
        统一攻击日志上报主循环。

        每隔 ATTACK_LOG_UPLOAD_INTERVAL 秒执行一次：
        1. 从所有检测器取出待上报事件
        2. 对所有事件立即执行 IP 封禁（独立于上报结果）
        3. 合并上次失败的重试缓冲
        4. 将事件规范化为统一字段格式
        5. 按 ATTACK_LOG_BATCH_SIZE 分批通过统一接口上报
        6. 上报失败则存入重试缓冲（下次尝试）
        """
        while not self._stop_event.is_set():
            try:
                self._do_upload_all()
            except Exception as e:
                logger.error(f"攻击日志上报循环异常: {e}")

            self._stop_event.wait(ATTACK_LOG_UPLOAD_INTERVAL)

    def _do_upload_all(self):
        """从所有检测器收集事件，归一化后统一上报"""
        # 从各检测器收集新事件
        new_events: List[dict] = []
        new_events.extend(port_scan_detector.get_recent_events(max_count=ATTACK_LOG_BATCH_SIZE))
        new_events.extend(web_attack_detector.get_recent_events(max_count=ATTACK_LOG_BATCH_SIZE))
        new_events.extend(payload_sniffer.get_recent_events(max_count=ATTACK_LOG_BATCH_SIZE))
        new_events.extend(process_monitor.get_recent_events(max_count=ATTACK_LOG_BATCH_SIZE))

        # 对所有新事件立即执行 IP 封禁（不等待上报结果）
        if new_events:
            self._block_attack_ips(new_events)

        # 合并重试缓冲
        with self._retry_lock:
            combined = self._retry_buffer + new_events
            self._retry_buffer = []

        if not combined:
            return

        # 分批处理
        to_send   = combined[:ATTACK_LOG_BATCH_SIZE]
        overflow  = combined[ATTACK_LOG_BATCH_SIZE:]

        # 规范化为统一字段格式
        normalized = [self._normalize_event(e) for e in to_send]

        success = self._upload_batch(normalized)

        # 上报失败：放回重试缓冲；溢出部分也回写
        with self._retry_lock:
            failed = normalized if not success else []
            self._retry_buffer = failed + overflow + self._retry_buffer
            if len(self._retry_buffer) > _MAX_PENDING_EVENTS:
                dropped = len(self._retry_buffer) - _MAX_PENDING_EVENTS
                self._retry_buffer = self._retry_buffer[-_MAX_PENDING_EVENTS:]
                logger.warning(f"攻击日志重试缓冲已满，丢弃最旧的 {dropped} 条")

    @staticmethod
    def _normalize_event(event: dict) -> dict:
        """
        将任意来源的攻击事件规范化为统一字段格式。

        各检测器的 to_dict() 输出字段不完全一致，规范化后服务端可用统一结构
        解析所有攻击类型，无需根据 attack_type 做特殊处理。
        """
        return {
            # ── 公共字段（所有攻击类型均有）──────────────────────────────────
            "attack_type":      event.get("attack_type", ""),
            "source_ip":        event.get("source_ip", ""),
            "level":            event.get("level", "low"),
            "detection_method": event.get("detection_method", ""),
            "timestamp":        event.get("timestamp") or event.get("end_time") or 0.0,
            "matched_pattern":  event.get("matched_pattern", ""),
            # ── Web/Payload 字段（端口扫描填空）──────────────────────────────
            "request_uri":      event.get("request_uri", ""),
            "request_method":   event.get("request_method", ""),
            "user_agent":       event.get("user_agent", ""),
            "referer":          event.get("referer", ""),
            "dest_port":        event.get("dest_port"),
            "protocol":         event.get("protocol", ""),
            "payload_snippet":  event.get("payload_snippet", ""),
            # ── 端口扫描专属字段（其他攻击类型填零/空）──────────────────────
            "target_ports":     event.get("target_ports", []),
            "port_count":       event.get("port_count", 0),
            "scan_type":        event.get("scan_type", ""),
            "start_time":       event.get("start_time", 0.0),
            "end_time":         event.get("end_time", 0.0),
            "duration":         event.get("duration", 0.0),
        }

    def _upload_batch(self, events: List[dict]) -> bool:
        """
        通过统一接口将一批事件上报至服务端。

        返回 True 表示上报成功，False 表示失败需重试。
        """
        if not events:
            return True

        try:
            client_id = config_manager.get_client_id()
            from network_client import network_client
            success, error = network_client.upload_attack_logs(client_id, events)
            if success:
                logger.info(f"攻击日志上报成功，共 {len(events)} 条")
                return True
            else:
                logger.warning(f"攻击日志上报失败: {error}，将在下次重试")
                return False
        except Exception as e:
            logger.error(f"攻击日志上报异常: {e}")
            return False


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

traffic_collector = TrafficCollector()
