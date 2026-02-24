# -*- coding: utf-8 -*-
"""
模块名称: payload_sniffer.py
模块功能: 基于端口的实时流量抓包与 Payload 攻击检测

检测方式:
    抓取指定端口的 TCP 流量，分析 Payload 中是否包含以下攻击行为：
        - SQL 注入         (sql_injection)
        - XSS 攻击         (xss_attempt)
        - 目录遍历         (dir_traversal)
        - 命令注入         (cmd_injection)
        - 远程代码执行     (rce_attempt)

上报策略:
    - 检测到事件后最多延迟 PAYLOAD_SNIFFER_UPLOAD_INTERVAL 秒上报（默认 10 秒）
    - 相同来源 IP + 攻击类型在 cooldown 秒内只上报一次（防刷）
    - 最多缓存 PAYLOAD_SNIFFER_QUEUE_MAX 条待上报事件

依赖:
    - scapy>=2.4.0（推荐，需要管理员 / root 权限）；
      缺失或权限不足时自动降级为原始 socket 方案。

系统适配: 所有平台通用（scapy 可用时效果最佳）
"""

import re
import time
import platform
import threading
import urllib.parse
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from constants import (
    ATTACK_TYPE_SQL_INJECTION,
    ATTACK_TYPE_XSS,
    ATTACK_TYPE_DIR_TRAVERSAL,
    ATTACK_TYPE_CMD_INJECTION,
    ATTACK_TYPE_RCE,
    ATTACK_LEVEL_HIGH,
    ATTACK_LEVEL_MEDIUM,
    ATTACK_LEVEL_LOW,
    PAYLOAD_SNIFFER_ENABLED,
    PAYLOAD_SNIFFER_PORTS,
    PAYLOAD_SNIFFER_UPLOAD_INTERVAL,
    PAYLOAD_SNIFFER_MAX_PAYLOAD_SIZE,
    PAYLOAD_SNIFFER_QUEUE_MAX,
    PAYLOAD_SNIFFER_COOLDOWN,
)
from logger import logger


# =============================================================================
# 攻击检测规则（模块加载时编译一次）
# =============================================================================

# 规则格式: (attack_type, level, description, compiled_pattern)
_RULES: List[Tuple[str, str, str, re.Pattern]] = []


def _build_rules() -> None:
    """编译所有攻击检测正则规则。"""
    raw_rules = [
        # ── SQL 注入 ──────────────────────────────────────────────────────────
        (ATTACK_TYPE_SQL_INJECTION, ATTACK_LEVEL_HIGH,
         "UNION SELECT注入",
         r"union[\s\+%20]+select"),
        (ATTACK_TYPE_SQL_INJECTION, ATTACK_LEVEL_HIGH,
         "布尔盲注",
         r"(?:or|and)[\s\+%20]+['\"]?1['\"]?[\s\+%20]*=[\s\+%20]*['\"]?1"),
        (ATTACK_TYPE_SQL_INJECTION, ATTACK_LEVEL_HIGH,
         "时间盲注",
         r"(?:sleep|benchmark|waitfor[\s]+delay)\s*\("),
        (ATTACK_TYPE_SQL_INJECTION, ATTACK_LEVEL_HIGH,
         "DDL/DML注入",
         r"(?:drop|truncate|delete|alter)[\s\+%20]+(?:table|database|from)"),
        (ATTACK_TYPE_SQL_INJECTION, ATTACK_LEVEL_HIGH,
         "危险存储过程",
         r"(?:xp_cmdshell|sp_executesql|exec\s*\()"),
        (ATTACK_TYPE_SQL_INJECTION, ATTACK_LEVEL_MEDIUM,
         "系统函数探测",
         r"(?:user\(\)|version\(\)|database\(\)|@@version|@@datadir)"),
        (ATTACK_TYPE_SQL_INJECTION, ATTACK_LEVEL_MEDIUM,
         "注释符注入(含值上下文)",
         r"(?:'[^']*|\"[^\"]*|\b\d+)\s*(?:--|/\*[\s\S]*?\*/)"),

        # ── XSS 攻击 ──────────────────────────────────────────────────────────
        (ATTACK_TYPE_XSS, ATTACK_LEVEL_MEDIUM,
         "script标签注入",
         r"<\s*script[\s>]"),
        (ATTACK_TYPE_XSS, ATTACK_LEVEL_MEDIUM,
         "javascript协议",
         r"javascript\s*:"),
        (ATTACK_TYPE_XSS, ATTACK_LEVEL_MEDIUM,
         "DOM内联事件",
         r"on(?:click|load|error|mouseover|submit|focus|blur|change|input|keypress|keydown|keyup)\s*="),
        (ATTACK_TYPE_XSS, ATTACK_LEVEL_MEDIUM,
         "document对象访问",
         r"document\.(?:cookie|location|write|getElementById)"),
        (ATTACK_TYPE_XSS, ATTACK_LEVEL_LOW,
         "SVG/img事件注入",
         r"<\s*(?:img|svg|body|input)[^>]+on\w+\s*="),

        # ── 目录遍历 ──────────────────────────────────────────────────────────
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_MEDIUM,
         "多层路径遍历",
         r"(?:(?:\.\./){2,}|(?:\.\.\\){2,}|(?:%2e%2e%2f){2,}|(?:%2e%2e/){2,}|(?:\.\.%2f){2,})"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_HIGH,
         "敏感系统文件访问",
         r"(?:/etc/(?:passwd|shadow|sudoers|group|hosts)|windows/(?:win\.ini|system32)|\.env\b|/\.git/)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_MEDIUM,
         "Unicode编码遍历",
         r"(?:%c0%af|%c1%9c|%u2215|%u2216)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_MEDIUM,
         "URL编码反斜杠遍历",
         r"\.\.%5[cC]"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_HIGH,
         "Web应用配置文件遍历",
         r"(?:wp-config\.php|web\.config|database\.yml|application\.properties|\.htpasswd)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_HIGH,
         "Java Web敏感目录遍历",
         r"WEB-INF/(?:web\.xml|classes|lib)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_HIGH,
         "SSH凭证文件访问",
         r"\.ssh/(?:authorized_keys|id_rsa|id_dsa|id_ed25519)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_MEDIUM,
         "空字节截断绕过",
         r"%00\.[a-zA-Z]{2,5}(?:\s|$|&)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_MEDIUM,
         "file://协议本地文件包含",
         r"file://+/?"),

        # ── 命令注入 ──────────────────────────────────────────────────────────
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "Shell分隔符注入",
         r"(?:;|\||&&|\|\|)\s*(?:ls|cat|id|whoami|uname|pwd|ifconfig|ipconfig|net\s+user)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "命令替换",
         r"(?:\$\([^)]{1,200}\)|`[^`]{1,200}`)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "反弹Shell",
         r"(?:bash\s+-i\s*>&|nc\s+(?:-\w+\s+)*-e\s+/bin|/dev/tcp/\d|python\s+-c\s*['\"]import socket)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "Windows命令注入",
         r"(?:cmd(?:\.exe)?\s*/[ck]|powershell\s+(?:-\w+\s+)*-[eE]nc|\bwscript\b)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "PowerShell绕过执行策略或编码命令",
         r"powershell(?:\.exe)?\s+(?:.*-[eE](?:nc|ncodedCommand|C)\s+[A-Za-z0-9+/=]{16,}|.*-[eE]xecutionPolicy\s+[bB]ypass)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "PowerShell远程下载执行",
         r"(?:IEX|Invoke-Expression|DownloadString|DownloadFile)\s*\("),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "Windows LOLBins文件下载执行",
         r"(?:certutil|bitsadmin|mshta|regsvr32|rundll32)\s+"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_MEDIUM,
         "下载并管道执行",
         r"(?:wget|curl)\s+\S+\s*\|\s*(?:ba)?sh"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_MEDIUM,
         "IFS注入绕过空格过滤",
         r"\$\{IFS\}|\$IFS(?:\s|$|;)"),

        # ── 远程代码执行 ──────────────────────────────────────────────────────
        (ATTACK_TYPE_RCE, ATTACK_LEVEL_HIGH,
         "PHP代码执行",
         r"(?:eval\s*\(|system\s*\(|passthru\s*\(|shell_exec\s*\(|assert\s*\()"),
        (ATTACK_TYPE_RCE, ATTACK_LEVEL_HIGH,
         "PHP伪协议",
         r"php://(?:input|filter|data)"),
        (ATTACK_TYPE_RCE, ATTACK_LEVEL_HIGH,
         "模板注入(SSTI)",
         r"(?:\{\{.{1,100}\}\}|\$\{.{1,100}\}|<%=?.{1,100}%>)"),
        (ATTACK_TYPE_RCE, ATTACK_LEVEL_HIGH,
         "Log4Shell",
         r"\$\{jndi:(?:ldap|rmi|dns|iiop)://"),
        (ATTACK_TYPE_RCE, ATTACK_LEVEL_HIGH,
         "Python代码执行",
         r"(?:__import__\s*\(|exec\s*\(|compile\s*\(|globals\s*\(\s*\))"),
    ]

    for attack_type, level, desc, raw_pattern in raw_rules:
        try:
            _RULES.append((
                attack_type, level, desc,
                re.compile(raw_pattern, re.IGNORECASE | re.DOTALL),
            ))
        except re.error as exc:
            logger.warning(f"[PayloadSniffer] 规则编译失败 [{desc}]: {exc}")


_build_rules()


# =============================================================================
# 内部哨兵异常（模块私有，不对外暴露）
# =============================================================================

class _WinPcapMissing(Exception):
    """scapy 检测到 WinPcap/Npcap 未安装时由 _sniff_with_scapy 抛出，
    供 _sniff_worker 捕获后切换到原始 socket 降级方案。"""


# =============================================================================
# 事件数据结构
# =============================================================================

@dataclass
class PayloadAttackEvent:
    """单次 Payload 攻击检测事件。"""

    attack_type: str        # 攻击类型标识
    source_ip: str          # 来源 IP
    dest_port: int          # 被监控的目标端口
    protocol: str           # 传输协议（TCP）
    matched_pattern: str    # 命中的规则描述
    level: str              # 威胁等级
    timestamp: float        # Unix 时间戳
    payload_snippet: str = ""   # payload 摘要（最多 200 字符）
    request_uri: str = ""       # HTTP 请求 URI（若能解析）
    request_method: str = ""    # HTTP 请求方法（若能解析）
    detection_method: str = "payload_capture"
    # Web 专属字段（抓包检测不适用，填空占位保持结构一致）
    user_agent: str = ""
    referer: str = ""

    def to_dict(self) -> dict:
        return {
            # ── 公共字段 ──────────────────────────────────────────────────────
            "attack_type":      self.attack_type,
            "source_ip":        self.source_ip,
            "request_uri":      self.request_uri[:500] if self.request_uri else "",
            "request_method":   self.request_method,
            "matched_pattern":  self.matched_pattern,
            "timestamp":        self.timestamp,
            "level":            self.level,
            "detection_method": self.detection_method,
            # ── Web 专属（抓包检测不适用，填空）─────────────────────────────
            "user_agent":       self.user_agent,
            "referer":          self.referer,
            # ── Payload 专属 ─────────────────────────────────────────────────
            "dest_port":        self.dest_port,
            "protocol":         self.protocol,
            "payload_snippet":  self.payload_snippet[:200] if self.payload_snippet else "",
        }


# =============================================================================
# PayloadSniffer 主类
# =============================================================================

class PayloadSniffer:
    """
    基于端口的流量 Payload 攻击检测器（单例）。

    线程模型:
        - SnifferThread: 使用 scapy / 原始 socket 持续抓包（守护线程）
        - 检测到的事件写入 _event_queue，由 TrafficCollector 的上报线程定期取走
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if PayloadSniffer._initialized:
            return

        self._running = False
        self._stop_event = threading.Event()
        self._sniff_thread: Optional[threading.Thread] = None

        # 有界事件队列（maxlen 自动淘汰最旧事件）
        self._event_queue: deque = deque(maxlen=PAYLOAD_SNIFFER_QUEUE_MAX)
        self._event_lock = threading.Lock()

        # 冷却表：(source_ip, attack_type) -> last_alert_time
        self._cooldown: Dict[Tuple[str, str], float] = {}
        self._cooldown_lock = threading.Lock()

        # 统计
        self._total_packets = 0
        self._total_events = 0

        PayloadSniffer._initialized = True

    # -------------------------------------------------------------------------
    # 生命周期
    # -------------------------------------------------------------------------

    def start(self) -> dict:
        """启动 Payload 嗅探器。返回当前状态字典。"""
        if not PAYLOAD_SNIFFER_ENABLED:
            logger.info("[PayloadSniffer] 已禁用（payload_sniffer.enabled=false）")
            return {"enabled": False, "running": False}

        if self._running:
            return self.get_status()

        self._running = True
        self._stop_event.clear()

        self._sniff_thread = threading.Thread(
            target=self._sniff_worker,
            name="PayloadSnifferThread",
            daemon=True,
        )
        self._sniff_thread.start()

        ports_str = ", ".join(str(p) for p in sorted(PAYLOAD_SNIFFER_PORTS))
        logger.info(f"[PayloadSniffer] 已启动，监控端口: [{ports_str}]")
        return self.get_status()

    def stop(self) -> None:
        """停止嗅探器，等待线程退出（最多 8 秒）。"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._sniff_thread and self._sniff_thread.is_alive():
            self._sniff_thread.join(timeout=8)

        logger.info("[PayloadSniffer] 已停止")

    def get_status(self) -> dict:
        with self._event_lock:
            queue_size = len(self._event_queue)
        return {
            "enabled":         PAYLOAD_SNIFFER_ENABLED,
            "running":         self._running,
            "monitored_ports": sorted(PAYLOAD_SNIFFER_PORTS),
            "queue_size":      queue_size,
            "total_packets":   self._total_packets,
            "total_events":    self._total_events,
        }

    def get_recent_events(self, max_count: int = 50) -> List[dict]:
        """
        从队列头部取出最多 max_count 条事件并返回其字典形式。
        取出后事件从队列中删除。
        """
        result = []
        with self._event_lock:
            count = min(max_count, len(self._event_queue))
            for _ in range(count):
                result.append(self._event_queue.popleft())
        return [e.to_dict() for e in result]

    # -------------------------------------------------------------------------
    # 嗅探线程
    # -------------------------------------------------------------------------

    def _sniff_worker(self) -> None:
        """
        嗅探工作线程，三段降级链：
            1. scapy + WinPcap/Npcap（BPF 精确过滤，效果最佳）
            2. 原始 socket + SIO_RCVALL（无需 WinPcap，需管理员权限）
            3. 报错退出，不影响其他检测模块
        """
        try:
            import scapy.all as scapy  # type: ignore
            logger.debug("[PayloadSniffer] 使用 scapy 进行数据包捕获")
            self._sniff_with_scapy(scapy)
        except ImportError:
            logger.warning("[PayloadSniffer] scapy 未安装，降级为原始 socket 嗅探")
            self._sniff_with_raw_socket()
        except _WinPcapMissing:
            logger.warning(
                "[PayloadSniffer] 未检测到 WinPcap/Npcap，"
                "降级为原始 socket（SIO_RCVALL）嗅探。"
                "如需最佳性能，建议安装 Npcap: https://npcap.com/"
            )
            self._sniff_with_raw_socket()
        except Exception as exc:
            if not self._stop_event.is_set():
                logger.error(f"[PayloadSniffer] 嗅探器启动失败: {exc}")
            self._running = False

    # ── scapy 方案 ────────────────────────────────────────────────────────────

    def _sniff_with_scapy(self, scapy) -> None:
        """
        使用 scapy L2 抓包（需要 WinPcap/Npcap on Windows）。

        若检测到 WinPcap/Npcap 缺失，抛出 _WinPcapMissing 让调用方
        决定如何降级，而不是在这里静默吞掉错误。
        """
        if PAYLOAD_SNIFFER_PORTS:
            bpf_filter = " or ".join(f"tcp port {p}" for p in sorted(PAYLOAD_SNIFFER_PORTS))
        else:
            bpf_filter = "tcp"

        logger.debug(f"[PayloadSniffer] BPF 过滤器: {bpf_filter}")
        try:
            scapy.sniff(
                filter=bpf_filter,
                prn=lambda pkt: self._process_scapy_packet(pkt, scapy),
                stop_filter=lambda _: self._stop_event.is_set(),
                store=0,
            )
        except Exception as exc:
            if self._stop_event.is_set():
                return
            err = str(exc).lower()
            if any(kw in err for kw in ("winpcap", "npcap", "layer 2", "not available at layer")):
                raise _WinPcapMissing(str(exc)) from exc
            logger.error(f"[PayloadSniffer] scapy 嗅探异常: {exc}")

    def _process_scapy_packet(self, pkt, scapy) -> None:
        """处理单个 scapy 数据包，提取 TCP payload 并分析。"""
        try:
            if not pkt.haslayer(scapy.TCP):
                return

            tcp = pkt[scapy.TCP]
            src_port: int = tcp.sport
            dst_port: int = tcp.dport

            # 确认至少一端是被监控端口
            if dst_port not in PAYLOAD_SNIFFER_PORTS and src_port not in PAYLOAD_SNIFFER_PORTS:
                return

            monitored_port = dst_port if dst_port in PAYLOAD_SNIFFER_PORTS else src_port

            # 提取来源 IP
            if pkt.haslayer(scapy.IP):
                src_ip: str = pkt[scapy.IP].src
            elif pkt.haslayer(scapy.IPv6):
                src_ip = pkt[scapy.IPv6].src
            else:
                src_ip = "unknown"

            raw_payload = bytes(tcp.payload)
            if not raw_payload:
                return

            self._total_packets += 1

            if len(raw_payload) > PAYLOAD_SNIFFER_MAX_PAYLOAD_SIZE:
                raw_payload = raw_payload[:PAYLOAD_SNIFFER_MAX_PAYLOAD_SIZE]

            self._analyze_payload(src_ip, monitored_port, "TCP", raw_payload)

        except Exception as exc:
            logger.debug(f"[PayloadSniffer] 数据包处理异常: {exc}")

    # ── 原始 socket 降级方案 ──────────────────────────────────────────────────

    @staticmethod
    def _get_local_ip() -> str:
        """
        获取本机主要出口 IPv4 地址。

        用 UDP 探测法（不实际发包）得到系统选择的出口 IP；
        失败时回退到 gethostbyname，最终兜底返回 127.0.0.1。
        """
        import socket as _socket
        try:
            probe = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            probe.settimeout(1)
            probe.connect(("192.168.0.1", 1))   # 不实际发包，只触发路由选择
            ip = probe.getsockname()[0]
            probe.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
        try:
            return _socket.gethostbyname(_socket.gethostname())
        except Exception:
            return "127.0.0.1"

    def _sniff_with_raw_socket(self) -> None:
        """
        原始 socket 嗅探（需要管理员 / root 权限）。

        Windows 注意事项：
            SIO_RCVALL 要求 socket 绑定到具体的本机 IP（不能用 0.0.0.0），
            否则会返回 WSAEINVAL (10022)。
        Linux 注意事项：
            AF_PACKET 收到的是以太帧（含 14 字节以太头），
            _process_raw_packet 解析时需要跳过该偏移。
        """
        import socket as _socket

        is_windows = platform.system() == "Windows"
        eth_offset = 0  # Windows IP raw socket 无以太头；Linux AF_PACKET 有

        try:
            if is_windows:
                # SIO_RCVALL 必须绑定到真实本机 IP，不能是 0.0.0.0
                local_ip = self._get_local_ip()
                logger.debug(f"[PayloadSniffer] 原始 socket 绑定到 {local_ip}")
                sock = _socket.socket(_socket.AF_INET, _socket.SOCK_RAW, _socket.IPPROTO_IP)
                sock.bind((local_ip, 0))
                sock.setsockopt(_socket.IPPROTO_IP, _socket.IP_HDRINCL, 1)
                sock.ioctl(_socket.SIO_RCVALL, _socket.RCVALL_ON)
            else:
                # Linux AF_PACKET 收到完整以太帧，需要跳过 14 字节以太头
                eth_offset = 14
                sock = _socket.socket(_socket.AF_PACKET, _socket.SOCK_RAW,
                                      _socket.htons(0x0800))

            sock.settimeout(1.0)
            logger.debug("[PayloadSniffer] 原始 socket 嗅探已启动")

            try:
                while not self._stop_event.is_set():
                    try:
                        raw_data, _ = sock.recvfrom(65535)
                        self._process_raw_packet(raw_data, eth_offset)
                    except _socket.timeout:
                        continue
                    except Exception:
                        break
            finally:
                if is_windows:
                    try:
                        sock.ioctl(_socket.SIO_RCVALL, _socket.RCVALL_OFF)
                    except Exception:
                        pass
                sock.close()

        except PermissionError:
            logger.error(
                "[PayloadSniffer] 原始 socket 需要管理员 / root 权限，"
                "Payload 嗅探功能不可用。请以管理员身份运行程序。"
            )
            self._running = False
        except OSError as exc:
            # WSAEACCES (10013) = 权限不足；其余按普通异常处理
            if getattr(exc, "winerror", None) == 10013:
                logger.error(
                    "[PayloadSniffer] 原始 socket 需要管理员权限（WSAEACCES），"
                    "Payload 嗅探功能不可用。"
                )
            else:
                logger.error(f"[PayloadSniffer] 原始 socket 嗅探异常: {exc}")
            self._running = False
        except Exception as exc:
            logger.error(f"[PayloadSniffer] 原始 socket 嗅探异常: {exc}")
            self._running = False

    def _process_raw_packet(self, raw_data: bytes, eth_offset: int = 0) -> None:
        """
        解析原始包，提取 TCP payload。

        参数:
            raw_data:   recvfrom 收到的原始字节
            eth_offset: 以太头偏移字节数（Linux AF_PACKET = 14，Windows = 0）
        """
        try:
            data = raw_data[eth_offset:]

            if len(data) < 20:
                return

            # IP 头长度 = IHL（字节 0 低 4 位）× 4
            ihl = (data[0] & 0x0F) * 4
            protocol = data[9]
            if protocol != 6:       # 6 = TCP
                return

            src_ip = f"{data[12]}.{data[13]}.{data[14]}.{data[15]}"

            if len(data) < ihl + 20:
                return

            # TCP 头部字段
            tcp_off = ihl
            src_port = (data[tcp_off] << 8) | data[tcp_off + 1]
            dst_port = (data[tcp_off + 2] << 8) | data[tcp_off + 3]

            if dst_port not in PAYLOAD_SNIFFER_PORTS and src_port not in PAYLOAD_SNIFFER_PORTS:
                return

            monitored_port = dst_port if dst_port in PAYLOAD_SNIFFER_PORTS else src_port

            # TCP 数据偏移 = 字节 12 高 4 位 × 4
            data_offset = ((data[tcp_off + 12] >> 4) & 0xF) * 4
            payload_start = tcp_off + data_offset
            raw_payload = data[payload_start:]

            if not raw_payload:
                return

            self._total_packets += 1

            if len(raw_payload) > PAYLOAD_SNIFFER_MAX_PAYLOAD_SIZE:
                raw_payload = raw_payload[:PAYLOAD_SNIFFER_MAX_PAYLOAD_SIZE]

            self._analyze_payload(src_ip, monitored_port, "TCP", raw_payload)

        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Payload 分析
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_tls(raw_payload: bytes) -> bool:
        """
        判断 payload 是否为 TLS/SSL 加密记录。

        TLS 记录层格式（RFC 5246）：
          Byte 0: Content-Type  (0x14=ChangeCipherSpec, 0x15=Alert,
                                 0x16=Handshake, 0x17=ApplicationData)
          Byte 1: Major version (0x03 for SSL3/TLS1.x/TLS1.3)
          Byte 2: Minor version (0x00–0x04)

        加密流量无法做明文攻击检测，应直接跳过以避免误报。
        """
        if len(raw_payload) < 3:
            return False
        content_type = raw_payload[0]
        major_ver    = raw_payload[1]
        minor_ver    = raw_payload[2]
        return content_type in (0x14, 0x15, 0x16, 0x17) \
               and major_ver == 0x03 \
               and minor_ver <= 0x04

    def _analyze_payload(self, src_ip: str, dest_port: int,
                         protocol: str, raw_payload: bytes) -> None:
        """对单个数据包的 payload 进行多规则攻击检测。"""
        # TLS/SSL 加密流量：密文无法做明文匹配，直接跳过，避免误报
        if self._is_tls(raw_payload):
            return

        # 宽松解码
        try:
            text = raw_payload.decode("utf-8", errors="replace")
        except Exception:
            try:
                text = raw_payload.decode("latin-1", errors="replace")
            except Exception:
                return

        # 非文本流量（可打印字符占比过低）也跳过，避免二进制数据产生误报
        printable_ratio = sum(
            1 for c in text if 0x20 <= ord(c) <= 0x7e or c in "\t\r\n"
        ) / max(len(text), 1)
        if printable_ratio < 0.5:
            return

        # URL 解码（一层）
        try:
            decoded = urllib.parse.unquote(text)
        except Exception:
            decoded = text

        # 解析 HTTP 请求行（若存在）
        method, uri = self._parse_http_request_line(text)

        now = time.time()

        for attack_type, level, desc, pattern in _RULES:
            # 同时检查原文和 URL 解码后的文本
            match = pattern.search(text) or (decoded != text and pattern.search(decoded))
            if not match:
                continue

            # 冷却检查：同 IP + 同攻击类型在 cooldown 秒内只告警一次
            if self._is_in_cooldown(src_ip, attack_type):
                continue

            # 提取命中位置的上下文摘要，清洗不可打印字符后存储
            hit = pattern.search(decoded) or pattern.search(text)
            if hit:
                snip_start = max(0, hit.start() - 40)
                snip_end = min(len(decoded), hit.end() + 40)
                snippet = self._sanitize_text(decoded[snip_start:snip_end])
            else:
                snippet = self._sanitize_text(decoded)

            event = PayloadAttackEvent(
                attack_type=attack_type,
                source_ip=src_ip,
                dest_port=dest_port,
                protocol=protocol,
                matched_pattern=desc,
                level=level,
                timestamp=now,
                payload_snippet=snippet,
                request_uri=self._sanitize_text(uri, max_len=500) if uri else "",
                request_method=method,
            )

            with self._event_lock:
                self._event_queue.append(event)

            self._total_events += 1
            self._update_cooldown(src_ip, attack_type)

            logger.warning(
                f"[PayloadSniffer] 检测到攻击 | 类型={attack_type} "
                f"来源={src_ip} 端口={dest_port} 规则={desc} 等级={level}"
            )

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------

    @staticmethod
    def _sanitize_text(text: str, max_len: int = 200) -> str:
        """
        将任意解码字符串清洗为可安全传输的纯文本。

        处理规则：
          - 保留可打印 ASCII (0x20–0x7e) 和常见空白 (\\t \\r \\n)
          - Unicode 替换字符 (\\ufffd) 及其他不可打印字符替换为 '.'
          - 截断到 max_len 字符
        """
        cleaned = re.sub(r'[^\x20-\x7e\t\r\n]', '.', text)
        return cleaned[:max_len]

    @staticmethod
    def _parse_http_request_line(text: str) -> Tuple[str, str]:
        """从文本首行提取 HTTP 请求方法和 URI。"""
        try:
            first_line = text.split("\n", 1)[0].strip()
            parts = first_line.split(" ", 2)
            if len(parts) >= 2:
                method = parts[0].upper()
                if method in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                    return method, parts[1]
        except Exception:
            pass
        return "", ""

    def _is_in_cooldown(self, src_ip: str, attack_type: str) -> bool:
        key = (src_ip, attack_type)
        with self._cooldown_lock:
            last = self._cooldown.get(key)
            return last is not None and (time.time() - last) < PAYLOAD_SNIFFER_COOLDOWN

    def _update_cooldown(self, src_ip: str, attack_type: str) -> None:
        key = (src_ip, attack_type)
        with self._cooldown_lock:
            self._cooldown[key] = time.time()
            # 防止冷却表无限增长：超过 2000 条时清理已过期记录
            if len(self._cooldown) > 2000:
                cutoff = time.time() - PAYLOAD_SNIFFER_COOLDOWN
                self._cooldown = {
                    k: v for k, v in self._cooldown.items() if v > cutoff
                }


# =============================================================================
# 全局单例
# =============================================================================

payload_sniffer = PayloadSniffer()
