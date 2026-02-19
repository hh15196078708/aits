# -*- coding: utf-8 -*-
"""
模块名称: port_scan_detector.py
模块功能: 检测对服务器的端口扫描行为（支持 Windows 和 Linux）
依赖模块:
    - 标准库: threading, time, collections, socket, os, platform, re
    - 第三方库: psutil>=5.9.0（连接监控）, scapy（可选，数据包嗅探）
系统适配: Windows 7/10/11/Server, Linux (Ubuntu/CentOS/Debian/Fedora 等)

检测方法说明:
    1. 连接监控法 (psutil):
       - 定期采集 net_connections()，统计同一源IP在时间窗口内访问的本地端口数量
       - 无需管理员权限，跨平台通用
       - 可检测: TCP 全连接扫描 (connect scan)

    2. 数据包嗅探法 (scapy):
       - 实时捕获原始网络包，分析 TCP 标志位和 UDP 流量
       - 需要管理员 (Windows) 或 root (Linux) 权限
       - 可检测: SYN 扫描、FIN 扫描、NULL 扫描、XMAS 扫描、UDP 扫描、ACK 扫描

    3. 日志分析法:
       - Windows: 读取安全事件日志 (Event ID 5156/5157)
       - Linux: 解析 iptables DROP/REJECT 记录 (/var/log/kern.log 等)
       - 无需额外权限（Windows 需要读日志权限）

检测逻辑:
    - 时间窗口: port_scan_time_window 秒（默认10秒）内
    - 阈值: 同一源IP访问超过 port_scan_port_count 个不同本地端口（默认20个）
    - 冷却: 同一IP触发后 60 秒内不重复告警
    - 等级: LOW（20+端口）、MEDIUM（40+端口）、HIGH（100+端口）
"""

import os
import re
import time
import socket
import platform
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Callable, Tuple

from constants import (
    ATTACK_TYPE_PORT_SCAN,
    ATTACK_LEVEL_HIGH,
    ATTACK_LEVEL_MEDIUM,
    ATTACK_LEVEL_LOW,
    DEFAULT_THRESHOLDS,
)
from logger import logger

# ---------------------------------------------------------------------------
# 可选依赖检测
# ---------------------------------------------------------------------------
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil 未安装，连接监控检测不可用")

try:
    from scapy.all import sniff, IP, TCP, UDP, ICMP  # noqa: F401
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class PortScanEvent:
    """端口扫描事件，包含检测结果的完整信息"""
    source_ip: str           # 扫描来源 IP
    target_ports: Set[int]   # 被扫描的本地端口集合
    scan_type: str           # 扫描类型标识
    start_time: float        # 检测窗口开始时间戳
    end_time: float          # 检测时间戳
    port_count: int          # 扫描端口总数
    level: str               # 威胁等级: low / medium / high
    detection_method: str    # 检测方式: connection / packet / log

    def to_dict(self) -> dict:
        """序列化为可上报的字典"""
        return {
            "attack_type": ATTACK_TYPE_PORT_SCAN,
            "source_ip": self.source_ip,
            "target_ports": sorted(self.target_ports)[:50],  # 最多记录50个端口
            "port_count": self.port_count,
            "scan_type": self.scan_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.end_time - self.start_time, 2),
            "level": self.level,
            "detection_method": self.detection_method,
        }


# ---------------------------------------------------------------------------
# 滑动时间窗口追踪器
# ---------------------------------------------------------------------------

class SlidingWindowTracker:
    """
    滑动时间窗口追踪器

    维护每个源IP在时间窗口内访问的端口集合。
    使用双端队列（deque）按时间顺序存储记录，惰性清除过期数据。
    线程安全。
    """

    def __init__(self, window_seconds: float):
        self._window = window_seconds
        # source_ip -> deque of (timestamp, local_port)
        self._data: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def record(self, source_ip: str, local_port: int) -> Set[int]:
        """
        记录一次端口访问，返回该IP在当前时间窗口内访问的所有端口集合。
        """
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            q = self._data[source_ip]
            q.append((now, local_port))
            # 惰性清除窗口外的旧记录
            while q and q[0][0] < cutoff:
                q.popleft()
            return {port for _, port in q}

    def get_ports(self, source_ip: str) -> Set[int]:
        """获取某IP在当前窗口内访问的端口集合（不记录新访问）"""
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            q = self._data[source_ip]
            while q and q[0][0] < cutoff:
                q.popleft()
            return {port for _, port in q}

    def cleanup_stale(self):
        """清理所有IP的过期数据，释放内存"""
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            for ip in list(self._data.keys()):
                q = self._data[ip]
                while q and q[0][0] < cutoff:
                    q.popleft()
                if not q:
                    del self._data[ip]

    def active_ip_count(self) -> int:
        """返回当前追踪的活跃IP数量"""
        with self._lock:
            return len(self._data)


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _get_local_ips() -> Set[str]:
    """获取本机所有IP地址（包括回环）"""
    ips = {"127.0.0.1", "::1", "0.0.0.0", "::"}
    try:
        hostname = socket.gethostname()
        ips.add(socket.gethostbyname(hostname))
    except Exception:
        pass
    if PSUTIL_AVAILABLE:
        try:
            for nic, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.address:
                        ips.add(addr.address)
        except Exception:
            pass
    return ips


def _classify_scan_level(port_count: int, threshold: int) -> str:
    """根据端口数量和阈值判断威胁等级"""
    if port_count >= threshold * 5:
        return ATTACK_LEVEL_HIGH
    elif port_count >= threshold * 2:
        return ATTACK_LEVEL_MEDIUM
    return ATTACK_LEVEL_LOW


def _is_admin() -> bool:
    """检测当前进程是否具有管理员/root权限"""
    if platform.system() == "Windows":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    else:
        return os.getuid() == 0


# ---------------------------------------------------------------------------
# 方法一：基于连接状态监控（psutil）
# ---------------------------------------------------------------------------

class ConnectionBasedDetector:
    """
    基于 psutil.net_connections() 的端口扫描检测

    原理:
        定期轮询系统当前网络连接表，统计每个外部源IP在时间窗口内
        发起连接的本地端口数。超过阈值则判定为端口扫描。

    优点: 不需要特权，Windows/Linux 通用
    局限: 只能发现 TCP 全连接扫描，半开扫描（SYN 扫描）在连接完成前
          可能已被关闭，取决于轮询频率
    """

    def __init__(self, port_threshold: int, time_window: float,
                 on_detect: Callable[[PortScanEvent], None]):
        self._threshold = port_threshold
        self._time_window = time_window
        self._on_detect = on_detect
        self._tracker = SlidingWindowTracker(time_window)
        self._reported: Dict[str, float] = {}   # ip -> last_report_timestamp
        self._report_cooldown = 60.0
        self._local_ips = _get_local_ips()
        self._local_ips_refresh = time.time()
        self._lock = threading.Lock()

    def _refresh_local_ips(self):
        """每5分钟刷新本机IP缓存"""
        if time.time() - self._local_ips_refresh > 300:
            self._local_ips = _get_local_ips()
            self._local_ips_refresh = time.time()

    def check(self) -> List[PortScanEvent]:
        """
        执行一次检测，返回本次发现的扫描事件列表。
        由外部定期调用（建议间隔 3~10 秒）。
        """
        events: List[PortScanEvent] = []
        if not PSUTIL_AVAILABLE:
            return events

        self._refresh_local_ips()
        now = time.time()

        try:
            # 获取所有 TCP/UDP 连接
            connections = psutil.net_connections(kind="inet")
        except psutil.AccessDenied:
            logger.debug("net_connections() 权限不足，尝试 tcp only")
            try:
                connections = psutil.net_connections(kind="tcp")
            except Exception:
                return events
        except Exception as e:
            logger.debug(f"net_connections() 异常: {e}")
            return events

        for conn in connections:
            if not conn.raddr or not conn.laddr:
                continue

            remote_ip = conn.raddr.ip
            local_port = conn.laddr.port

            # 过滤本机内部通信
            if not remote_ip or remote_ip in self._local_ips:
                continue
            # 过滤无效IP
            if remote_ip in ("0.0.0.0", "::", ""):
                continue

            ports_in_window = self._tracker.record(remote_ip, local_port)

            if len(ports_in_window) >= self._threshold:
                with self._lock:
                    last_report = self._reported.get(remote_ip, 0)
                    if now - last_report < self._report_cooldown:
                        continue
                    self._reported[remote_ip] = now

                event = PortScanEvent(
                    source_ip=remote_ip,
                    target_ports=ports_in_window.copy(),
                    scan_type="connect_scan",
                    start_time=now - self._time_window,
                    end_time=now,
                    port_count=len(ports_in_window),
                    level=_classify_scan_level(len(ports_in_window), self._threshold),
                    detection_method="connection",
                )
                events.append(event)

        return events


# ---------------------------------------------------------------------------
# 方法二：基于数据包嗅探（scapy）
# ---------------------------------------------------------------------------

class PacketBasedDetector:
    """
    基于 scapy 数据包嗅探的端口扫描检测

    支持的扫描类型:
        - SYN  扫描: TCP flags = SYN only（最常见的 nmap 默认扫描）
        - FIN  扫描: TCP flags = FIN only
        - NULL 扫描: TCP flags = 0（无任何标志位）
        - XMAS 扫描: TCP flags = FIN+PSH+URG
        - ACK  扫描: TCP flags = ACK only（用于探测防火墙规则）
        - UDP  扫描: 向多个UDP端口发包

    要求:
        - Windows: 需要管理员权限（以管理员身份运行）
        - Linux:   需要 root 权限或 CAP_NET_RAW capability

    说明:
        嗅探在独立守护线程中运行，通过 stop_filter 优雅退出。
        检测到扫描后直接调用 on_detect 回调，不缓存事件。
    """

    # TCP 标志位常量（Scapy 数字格式）
    FLAG_FIN = 0x01
    FLAG_SYN = 0x02
    FLAG_RST = 0x04
    FLAG_PSH = 0x08
    FLAG_ACK = 0x10
    FLAG_URG = 0x20

    def __init__(self, port_threshold: int, time_window: float,
                 on_detect: Callable[[PortScanEvent], None]):
        self._threshold = port_threshold
        self._time_window = time_window
        self._on_detect = on_detect
        self._tracker = SlidingWindowTracker(time_window)
        self._reported: Dict[str, float] = {}
        self._report_cooldown = 60.0
        self._lock = threading.Lock()
        self._sniff_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._local_ips = _get_local_ips()

    def _classify_tcp_flags(self, flags: int) -> Optional[str]:
        """
        根据 TCP 标志位判断扫描类型。
        正常握手（SYN、SYN+ACK、ACK）返回 None，不记录。
        """
        S = bool(flags & self.FLAG_SYN)
        A = bool(flags & self.FLAG_ACK)
        F = bool(flags & self.FLAG_FIN)
        P = bool(flags & self.FLAG_PSH)
        U = bool(flags & self.FLAG_URG)

        if S and not A:
            return "syn_scan"
        if not S and not A and not F and not P and not U:
            return "null_scan"
        if F and P and U:
            return "xmas_scan"
        if F and not S and not A:
            return "fin_scan"
        if A and not S and not P and not U:
            return "ack_scan"
        return None  # 正常数据包（如 ACK+PSH 数据传输），忽略

    def _handle_packet(self, packet):
        """Scapy 包回调，在嗅探线程中执行"""
        try:
            if IP not in packet:
                return

            src_ip = packet[IP].src
            # 过滤本机来源
            if src_ip in self._local_ips:
                return

            now = time.time()

            if TCP in packet:
                dst_port = packet[TCP].dport
                scan_type = self._classify_tcp_flags(int(packet[TCP].flags))
                if scan_type is None:
                    return  # 正常流量，跳过
                ports = self._tracker.record(src_ip, dst_port)
                self._check_and_report(src_ip, ports, scan_type, now)

            elif UDP in packet:
                dst_port = packet[UDP].dport
                ports = self._tracker.record(src_ip, dst_port)
                self._check_and_report(src_ip, ports, "udp_scan", now)

        except Exception as e:
            logger.debug(f"包处理异常: {e}")

    def _check_and_report(self, src_ip: str, ports: Set[int],
                          scan_type: str, now: float):
        """检查端口数量是否超过阈值，超过则触发告警"""
        if len(ports) < self._threshold:
            return
        with self._lock:
            if now - self._reported.get(src_ip, 0) < self._report_cooldown:
                return
            self._reported[src_ip] = now

        event = PortScanEvent(
            source_ip=src_ip,
            target_ports=ports.copy(),
            scan_type=scan_type,
            start_time=now - self._time_window,
            end_time=now,
            port_count=len(ports),
            level=_classify_scan_level(len(ports), self._threshold),
            detection_method="packet",
        )
        self._on_detect(event)

    def _sniff_loop(self):
        """嗅探主循环（在独立线程中运行）"""
        try:
            sniff(
                filter="tcp or udp",
                prn=self._handle_packet,
                store=False,
                stop_filter=lambda _: self._stop_event.is_set(),
            )
        except Exception as e:
            logger.error(f"数据包嗅探异常: {e}")

    def start(self) -> bool:
        """启动数据包嗅探，返回是否成功启动"""
        if not SCAPY_AVAILABLE:
            logger.info("scapy 不可用，跳过数据包嗅探检测")
            return False
        if not _is_admin():
            logger.info("权限不足（需要管理员/root），跳过数据包嗅探检测")
            return False

        try:
            self._stop_event.clear()
            self._sniff_thread = threading.Thread(
                target=self._sniff_loop,
                name="PortScanSniffThread",
                daemon=True,
            )
            self._sniff_thread.start()
            logger.info("数据包嗅探检测已启动（可检测 SYN/FIN/NULL/XMAS/ACK/UDP 扫描）")
            return True
        except Exception as e:
            logger.error(f"启动数据包嗅探失败: {e}")
            return False

    def stop(self):
        """停止数据包嗅探"""
        self._stop_event.set()
        if self._sniff_thread and self._sniff_thread.is_alive():
            self._sniff_thread.join(timeout=5)


# ---------------------------------------------------------------------------
# 方法三：基于系统日志分析
# ---------------------------------------------------------------------------

class LogBasedDetector:
    """
    基于系统日志的端口扫描检测

    Windows:
        读取 Windows 安全事件日志：
        - Event ID 5156: Windows Filtering Platform 允许连接
        - Event ID 5157: Windows Filtering Platform 阻断连接
        需要 pywin32 库和适当的事件日志读取权限。

    Linux:
        解析防火墙 DROP/REJECT 日志：
        - /var/log/kern.log  （Ubuntu/Debian）
        - /var/log/messages  （CentOS/RHEL/Fedora）
        - /var/log/syslog    （通用）
        日志中需含有 iptables 或 nftables 的记录（需提前配置日志规则）。

    说明:
        日志检测是对连接监控的补充，尤其适合检测被防火墙拦截的扫描探测。
        check() 方法每次调用只分析最近 N 行日志，性能开销低。
    """

    # Linux 日志文件优先级列表
    LINUX_LOG_FILES = [
        "/var/log/kern.log",
        "/var/log/messages",
        "/var/log/syslog",
        "/var/log/firewalld",
    ]

    # 匹配 iptables 日志的正则（提取 SRC= 和 DPT=）
    _IPTABLES_PATTERN = re.compile(
        r"SRC=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*?DPT=(\d+)",
        re.IGNORECASE,
    )

    def __init__(self, port_threshold: int, time_window: float,
                 on_detect: Callable[[PortScanEvent], None]):
        self._threshold = port_threshold
        self._time_window = time_window
        self._on_detect = on_detect
        self._tracker = SlidingWindowTracker(time_window)
        self._reported: Dict[str, float] = {}
        self._report_cooldown = 60.0
        self._lock = threading.Lock()
        self._platform = platform.system()
        # Linux: 记录已读取到的文件偏移量，避免重复解析
        self._log_offsets: Dict[str, int] = {}

    def check(self) -> List[PortScanEvent]:
        """执行一次日志扫描检测"""
        if self._platform == "Windows":
            return self._check_windows_event_log()
        elif self._platform == "Linux":
            return self._check_linux_log()
        return []

    # ---- Windows 事件日志 ----

    def _check_windows_event_log(self) -> List[PortScanEvent]:
        """读取 Windows 安全日志，检测端口扫描"""
        events: List[PortScanEvent] = []
        try:
            import win32evtlog  # pywin32
        except ImportError:
            return events  # pywin32 未安装

        try:
            handle = win32evtlog.OpenEventLog(None, "Security")
            flags = (win32evtlog.EVENTLOG_BACKWARDS_READ |
                     win32evtlog.EVENTLOG_SEQUENTIAL_READ)
            cutoff = time.time() - self._time_window
            now = time.time()

            while True:
                records = win32evtlog.ReadEventLog(handle, flags, 0)
                if not records:
                    break
                for record in records:
                    # Event ID 5156/5157：网络过滤平台连接记录
                    if record.EventID not in (5156, 5157):
                        continue
                    event_ts = record.TimeGenerated.timestamp()
                    if event_ts < cutoff:
                        # 日志是倒序读取的，早于窗口的记录可以停止
                        win32evtlog.CloseEventLog(handle)
                        return events

                    strings = record.StringInserts or []
                    if len(strings) < 8:
                        continue

                    # 事件字段顺序（参考 Microsoft 文档 Event 5156）:
                    # [0]=进程ID, [1]=应用名, [2]=方向,
                    # [3]=源IP, [4]=源端口, [5]=目标IP, [6]=目标端口, [7]=协议
                    src_ip = strings[3]
                    dst_port_str = strings[6]

                    if not src_ip or not dst_port_str.isdigit():
                        continue
                    dst_port = int(dst_port_str)
                    if dst_port == 0:
                        continue

                    ports = self._tracker.record(src_ip, dst_port)
                    if len(ports) >= self._threshold:
                        ev = self._make_event(src_ip, ports, "connect_scan",
                                              now, "log")
                        if ev:
                            events.append(ev)

            win32evtlog.CloseEventLog(handle)
        except Exception as e:
            logger.debug(f"Windows 事件日志读取异常: {e}")

        return events

    # ---- Linux 防火墙日志 ----

    def _check_linux_log(self) -> List[PortScanEvent]:
        """解析 Linux 防火墙日志，检测端口扫描"""
        events: List[PortScanEvent] = []
        now = time.time()

        for log_file in self.LINUX_LOG_FILES:
            if not os.path.isfile(log_file):
                continue
            try:
                size = os.path.getsize(log_file)
                offset = self._log_offsets.get(log_file, max(0, size - 65536))

                with open(log_file, "r", errors="ignore") as f:
                    f.seek(offset)
                    new_content = f.read()
                    self._log_offsets[log_file] = f.tell()

                for line in new_content.splitlines():
                    # 只处理 DROP 或 REJECT 的记录行
                    upper = line.upper()
                    if "DROP" not in upper and "REJECT" not in upper:
                        continue
                    m = self._IPTABLES_PATTERN.search(line)
                    if not m:
                        continue
                    src_ip = m.group(1)
                    dst_port = int(m.group(2))

                    ports = self._tracker.record(src_ip, dst_port)
                    if len(ports) >= self._threshold:
                        ev = self._make_event(src_ip, ports, "connect_scan",
                                              now, "log")
                        if ev:
                            events.append(ev)

                # 找到可读日志文件后退出循环
                break
            except PermissionError:
                logger.debug(f"无权限读取日志文件: {log_file}")
                continue
            except Exception as e:
                logger.debug(f"读取日志文件异常 {log_file}: {e}")
                continue

        return events

    # ---- 公共辅助 ----

    def _make_event(self, src_ip: str, ports: Set[int], scan_type: str,
                    now: float, method: str) -> Optional[PortScanEvent]:
        """构造事件，若在冷却期内则返回 None"""
        with self._lock:
            if now - self._reported.get(src_ip, 0) < self._report_cooldown:
                return None
            self._reported[src_ip] = now
        return PortScanEvent(
            source_ip=src_ip,
            target_ports=ports.copy(),
            scan_type=scan_type,
            start_time=now - self._time_window,
            end_time=now,
            port_count=len(ports),
            level=_classify_scan_level(len(ports), self._threshold),
            detection_method=method,
        )


# ---------------------------------------------------------------------------
# 主检测器：整合三种方法
# ---------------------------------------------------------------------------

class PortScanDetector:
    """
    端口扫描检测器（主类，单例）

    整合三种检测方法，统一管理生命周期，提供事件缓存和回调机制。

    使用示例:
        detector = port_scan_detector   # 全局单例
        detector.add_event_callback(my_callback)
        detector.start()
        # ... 运行期间自动检测 ...
        events = detector.get_recent_events()  # 取出待上报事件
        detector.stop()

    线程模型:
        - 主线程: 调用 start() / stop() / get_recent_events()
        - PortScanCheckThread: 定期执行连接监控和日志分析（非特权检测）
        - PortScanSniffThread: scapy 嗅探循环（需要特权，独立守护线程）
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if PortScanDetector._initialized:
            return

        thresholds = DEFAULT_THRESHOLDS
        self._port_threshold: int = thresholds.get("port_scan_port_count", 20)
        self._time_window: float = float(thresholds.get("port_scan_time_window", 10))
        self._check_interval: float = 5.0  # 连接监控轮询间隔（秒）

        # 事件缓存（待上报）
        self._pending_events: List[PortScanEvent] = []
        self._events_lock = threading.Lock()
        # 外部注册的回调列表
        self._callbacks: List[Callable[[PortScanEvent], None]] = []

        # 三种检测器实例
        self._conn_detector = ConnectionBasedDetector(
            self._port_threshold, self._time_window, self._dispatch_event
        )
        self._packet_detector = PacketBasedDetector(
            self._port_threshold, self._time_window, self._dispatch_event
        )
        self._log_detector = LogBasedDetector(
            self._port_threshold, self._time_window, self._dispatch_event
        )

        self._running = False
        self._stop_event = threading.Event()
        self._check_thread: Optional[threading.Thread] = None

        # 记录各检测方法的启动状态
        self._method_status: Dict[str, bool] = {
            "connection": False,
            "packet": False,
            "log": False,
        }

        PortScanDetector._initialized = True

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def add_event_callback(self, callback: Callable[[PortScanEvent], None]):
        """注册事件回调函数，每次检测到扫描时触发"""
        self._callbacks.append(callback)

    def start(self) -> Dict[str, bool]:
        """
        启动所有检测方法。

        返回各检测方法的启动状态字典，例如:
            {"connection": True, "packet": False, "log": True}
        """
        if self._running:
            return self._method_status.copy()

        self._running = True
        self._stop_event.clear()

        # 启动连接监控 + 日志分析的轮询线程
        if PSUTIL_AVAILABLE:
            self._check_thread = threading.Thread(
                target=self._polling_loop,
                name="PortScanCheckThread",
                daemon=True,
            )
            self._check_thread.start()
            self._method_status["connection"] = True
            logger.info("端口扫描检测 [连接监控] 已启动")
        else:
            self._method_status["connection"] = False
            logger.warning("端口扫描检测 [连接监控] 未启动（psutil 不可用）")

        # 启动数据包嗅探（需要权限）
        packet_ok = self._packet_detector.start()
        self._method_status["packet"] = packet_ok

        # 日志分析在轮询循环中执行，始终有效
        self._method_status["log"] = True
        logger.info(
            f"端口扫描检测已启动: 连接监控={self._method_status['connection']}, "
            f"数据包嗅探={self._method_status['packet']}, "
            f"日志分析={self._method_status['log']}"
        )
        logger.info(
            f"检测阈值: {self._port_threshold} 个端口 / {self._time_window} 秒"
        )

        return self._method_status.copy()

    def stop(self):
        """停止所有检测方法"""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self._packet_detector.stop()

        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=5)

        logger.info("端口扫描检测已停止")

    def get_recent_events(self, max_count: int = 100) -> List[dict]:
        """
        取出并清空待上报事件队列，返回序列化后的字典列表。
        建议由上报线程定期调用。
        """
        with self._events_lock:
            events = self._pending_events[:max_count]
            self._pending_events = self._pending_events[max_count:]
        return [e.to_dict() for e in events]

    def get_status(self) -> dict:
        """返回检测器当前运行状态"""
        with self._events_lock:
            pending = len(self._pending_events)
        return {
            "running": self._running,
            "psutil_available": PSUTIL_AVAILABLE,
            "scapy_available": SCAPY_AVAILABLE,
            "port_threshold": self._port_threshold,
            "time_window_seconds": self._time_window,
            "pending_events": pending,
            "method_status": self._method_status.copy(),
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _dispatch_event(self, event: PortScanEvent):
        """
        内部事件分发：缓存事件 + 调用外部回调 + 记录日志。
        由各检测器在检测到扫描时调用，可能在不同线程中执行。
        """
        with self._events_lock:
            self._pending_events.append(event)
            # 防止无限增长
            if len(self._pending_events) > 2000:
                self._pending_events = self._pending_events[-2000:]

        logger.warning(
            f"[端口扫描告警] "
            f"源IP={event.source_ip} "
            f"扫描类型={event.scan_type} "
            f"端口数={event.port_count} "
            f"威胁等级={event.level} "
            f"检测方法={event.detection_method}"
        )

        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"端口扫描事件回调异常: {e}")

    def _polling_loop(self):
        """
        连接监控 + 日志分析的轮询主循环。
        每隔 _check_interval 秒执行一次，使用 Event.wait() 实现可中断等待。
        """
        # 错开首次日志扫描，避免和启动时的连接峰值重叠
        cleanup_counter = 0

        while not self._stop_event.is_set():
            try:
                # 连接监控检测
                conn_events = self._conn_detector.check()
                for ev in conn_events:
                    self._dispatch_event(ev)

                # 日志分析检测
                log_events = self._log_detector.check()
                for ev in log_events:
                    self._dispatch_event(ev)

                # 每 10 次轮询清理一次滑动窗口的过期数据
                cleanup_counter += 1
                if cleanup_counter >= 10:
                    cleanup_counter = 0
                    self._conn_detector._tracker.cleanup_stale()
                    self._log_detector._tracker.cleanup_stale()

            except Exception as e:
                logger.error(f"端口扫描轮询异常: {e}")

            self._stop_event.wait(self._check_interval)


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

port_scan_detector = PortScanDetector()
