# -*- coding: utf-8 -*-
"""
模块名称: process_monitor.py
模块功能: 进程级命令注入与目录遍历攻击检测器

检测层次（补充 web 日志分析和流量抓包，覆盖攻击成功执行的场景）:
    1. Web 服务器异常子进程检测
       发现 Web 服务进程（apache/nginx/php-fpm/java 等）异常派生 Shell 或
       网络工具（bash/nc/powershell 等），识别命令注入成功执行的迹象。

    2. 进程命令行攻击特征匹配
       对所有新启动进程的命令行参数进行规则匹配，检测：
         - 反弹 Shell（bash -i >&、nc -e、/dev/tcp/）
         - PowerShell 绕过（-EncodedCommand、-ExecutionPolicy Bypass）
         - 下载执行（curl/wget | sh、IEX）
         - 直接读取敏感文件（cat /etc/passwd 等）
         - 路径遍历到敏感位置的命令行参数

    3. 敏感文件打开检测（Linux/macOS）
       对 Web 服务进程调用 open_files()，检查是否打开了
       /etc/passwd、.ssh/、wp-config.php 等敏感文件。

依赖:
    psutil >= 5.0（可选，缺失时模块自动禁用）

检测去重:
    - 以 (pid, attack_type) 为 key，冷却期内不重复告警
    - 以 (pid, create_time) 唯一标识进程，避免对同一进程重复分析
    - 程序运行期间发现的新进程才会被分析
"""

import os
import re
import time
import platform
import threading
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from constants import (
    ATTACK_TYPE_CMD_INJECTION,
    ATTACK_TYPE_DIR_TRAVERSAL,
    ATTACK_LEVEL_HIGH,
    ATTACK_LEVEL_MEDIUM,
    PROCESS_MONITOR_ENABLED,
    PROCESS_MONITOR_SCAN_INTERVAL,
    PROCESS_MONITOR_COOLDOWN,
)
from logger import logger

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False


# =============================================================================
# 已知 Web 服务进程名集合（匹配时忽略路径前缀和 .exe 后缀）
# =============================================================================

_WEB_SERVER_NAMES: FrozenSet[str] = frozenset({
    # Apache
    "apache", "apache2", "httpd", "httpd-worker",
    # Nginx
    "nginx",
    # PHP
    "php-fpm", "php-cgi", "php7.4-fpm", "php8.0-fpm",
    "php8.1-fpm", "php8.2-fpm", "php8.3-fpm",
    # Java（Tomcat / Spring Boot / Quarkus 等）
    "java",
    # Python WSGI/ASGI
    "gunicorn", "uwsgi", "waitress", "hypercorn", "daphne",
    # Node.js
    "node", "nodejs",
    # Ruby
    "ruby", "puma", "passenger", "unicorn",
    # Windows IIS
    "w3wp", "iisexpress",
})

# =============================================================================
# Web 服务进程派生后视为可疑的子进程名
# =============================================================================

_SUSPICIOUS_CHILD_NAMES: FrozenSet[str] = frozenset({
    # Unix Shell
    "bash", "sh", "dash", "zsh", "ksh", "csh", "tcsh", "fish",
    # Windows Shell
    "cmd", "powershell", "pwsh",
    # 网络工具（常用于反弹 Shell）
    "nc", "ncat", "netcat", "socat", "nmap",
    # 下载工具
    "wget", "curl",
})

# =============================================================================
# 进程命令行攻击特征规则
# =============================================================================

@dataclass
class _ProcRule:
    attack_type: str
    level: str
    desc: str
    pattern: re.Pattern


def _compile_proc_rules() -> List[_ProcRule]:
    """编译进程命令行攻击检测规则（模块加载时执行一次）。"""
    raw: List[Tuple[str, str, str, str]] = [
        # ── 反弹 Shell ────────────────────────────────────────────────────────
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "bash反弹Shell",
         r"bash\s+-i\s*>&\s*/dev/tcp/"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "nc反弹Shell(-e /bin/sh)",
         r"nc(?:at)?\s+(?:-\w+\s+)*-e\s+(?:/bin/(?:ba)?sh|cmd(?:\.exe)?)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "socat反弹Shell",
         r"socat\s+.*(?:tcp:|TCP:).*,exec:"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "Python反弹Shell",
         r"python\d*\s+-c\s+['\"].*(?:import\s+socket|\.connect\(|subprocess|os\.system)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "Perl反弹Shell",
         r"perl\s+-e\s+['\"].*(?:socket|/bin/(?:ba)?sh)"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "Ruby反弹Shell",
         r"ruby\s+-rsocket\s+-e"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "mkfifo命名管道反弹Shell",
         r"mkfifo\s+\S+.*(?:/bin/(?:ba)?sh|nc\s)"),
        # ── PowerShell 绕过 ───────────────────────────────────────────────────
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "PowerShell编码命令执行",
         r"powershell(?:\.exe)?\s+(?:.*-[eE](?:nc|ncodedCommand|C)\s+[A-Za-z0-9+/=]{20,})"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "PowerShell绕过执行策略",
         r"powershell(?:\.exe)?\s+.*-[eE]xecution[pP]olicy\s+[bB]ypass"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "PowerShell隐藏窗口执行",
         r"powershell(?:\.exe)?\s+.*-[wW]indow[sS]tyle\s+[hH]idden"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "PowerShell远程下载执行(IEX)",
         r"(?:IEX|Invoke-Expression|Invoke-WebRequest)\s*\(|DownloadString\s*\("),
        # ── Windows LOLBins ───────────────────────────────────────────────────
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "certutil远程下载文件",
         r"certutil\s+.*(?:-urlcache|-decode)\s+"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "bitsadmin下载执行",
         r"bitsadmin\s+.*(?:/transfer|/addfile)\s+"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "mshta远程执行",
         r"mshta\s+(?:https?://|javascript:|vbscript:)"),
        # ── 下载并执行脚本 ────────────────────────────────────────────────────
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_HIGH,
         "curl/wget下载管道执行",
         r"(?:curl|wget)\s+\S+\s*\|\s*(?:ba)?sh"),
        (ATTACK_TYPE_CMD_INJECTION, ATTACK_LEVEL_MEDIUM,
         "base64解码后执行",
         r"(?:echo\s+[A-Za-z0-9+/=]{20,}\s*\|\s*base64\s+-d|base64\s+-d\b.{0,100}\|\s*(?:ba)?sh)"),
        # ── 目录遍历：命令行路径参数 ──────────────────────────────────────────
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_HIGH,
         "命令行路径遍历读取敏感系统文件",
         r"(?:\.\./){2,}(?:etc/(?:passwd|shadow|sudoers)|windows/(?:system32|win\.ini)|proc/self/)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_HIGH,
         "直接读取/etc/passwd或shadow",
         r"(?:cat|type|more|less|head|tail|vi|nano)\s+/etc/(?:passwd|shadow|sudoers|group)\b"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_MEDIUM,
         "读取Web应用配置文件",
         r"(?:cat|type|more)\s+.*(?:wp-config\.php|web\.config|\.env\b|database\.yml|config\.php)"),
        (ATTACK_TYPE_DIR_TRAVERSAL, ATTACK_LEVEL_HIGH,
         "读取SSH私钥",
         r"(?:cat|more|head)\s+.*\.ssh/(?:id_rsa|id_dsa|id_ed25519|authorized_keys)\b"),
    ]

    rules: List[_ProcRule] = []
    for attack_type, level, desc, raw_pat in raw:
        try:
            rules.append(_ProcRule(
                attack_type=attack_type,
                level=level,
                desc=desc,
                pattern=re.compile(raw_pat, re.IGNORECASE),
            ))
        except re.error as exc:
            logger.warning(f"[ProcessMonitor] 规则编译失败 [{desc}]: {exc}")
    return rules


_PROC_RULES: List[_ProcRule] = _compile_proc_rules()

# =============================================================================
# 敏感文件路径模式（用于 open_files() 检测）
# =============================================================================

_SENSITIVE_FILE_RE = re.compile(
    r"(?:"
    r"/etc/(?:passwd|shadow|sudoers|group|crontab)|"
    r"/(?:root|home)/[^/]+/\.ssh/|"
    r"(?:wp-config|web\.config|\.htpasswd|\.env)(?:\b|$)|"
    r"(?:/proc/\d+/(?:mem|environ|maps))"
    r")",
    re.IGNORECASE,
)


# =============================================================================
# 事件数据结构
# =============================================================================

@dataclass
class ProcessAttackEvent:
    """
    进程监控攻击事件。

    序列化格式与 WebAttackEvent.to_dict() 保持一致，
    可直接通过 Web 攻击上报接口上传至服务端，无需新增接口。
    """
    attack_type: str        # ATTACK_TYPE_CMD_INJECTION 或 ATTACK_TYPE_DIR_TRAVERSAL
    pid: int                # 目标进程 PID
    process_name: str       # 目标进程名称
    cmdline: str            # 命令行（截断至 500 字符）
    parent_name: str        # 父进程名称（空字符串表示未知）
    matched_pattern: str    # 命中的规则描述
    timestamp: float        # Unix 时间戳
    level: str              # 威胁等级
    source_ip: str = ""     # 来源 IP（进程检测通常不可知，留空）
    detection_method: str = "process_monitor"

    def to_dict(self) -> dict:
        """序列化为与现有上报接口兼容的字典格式。"""
        # 将进程上下文信息编码到 payload_snippet
        snippet = (
            f"[parent={self.parent_name or 'unknown'}"
            f" -> child={self.process_name}(pid={self.pid})] "
            f"{self.cmdline}"
        )
        return {
            # ── 公共字段 ──────────────────────────────────────────────────────
            "attack_type":      self.attack_type,
            "source_ip":        self.source_ip,
            "request_uri":      "",
            "request_method":   "",
            "matched_pattern":  self.matched_pattern,
            "timestamp":        self.timestamp,
            "level":            self.level,
            "detection_method": self.detection_method,
            # ── Web 专属（进程检测不适用，留空）─────────────────────────────
            "user_agent":       "",
            "referer":          "",
            # ── Payload 专属（复用 payload_snippet 存储进程信息）─────────────
            "dest_port":        None,
            "protocol":         "",
            "payload_snippet":  snippet[:500],
        }


# =============================================================================
# ProcessMonitor 主类
# =============================================================================

class ProcessMonitor:
    """
    进程级攻击检测器（单例）。

    周期性扫描系统进程，对新出现的进程执行三类检测:
        1. Web 服务器子进程异常检测（web server -> shell/nc）
        2. 命令行攻击特征匹配（反弹 Shell / PowerShell 绕过等）
        3. 敏感文件打开检测（Linux/macOS，仅对 Web 进程）

    已分析过的进程（以 pid + create_time 唯一标识）在本次运行期间不再重复分析，
    同一进程同一攻击类型在 PROCESS_MONITOR_COOLDOWN 秒内只告警一次。
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ProcessMonitor._initialized:
            return

        self._running: bool = False
        self._stop_event = threading.Event()
        self._scan_thread: Optional[threading.Thread] = None

        # 待上报事件缓存
        self._pending_events: List[ProcessAttackEvent] = []
        self._events_lock = threading.Lock()

        # 冷却表：(pid, attack_type) -> last_alert_time
        self._cooldown: Dict[Tuple[int, str], float] = {}
        self._cooldown_lock = threading.Lock()

        # 已分析进程集合：(pid, create_time)，防止重复分析
        self._seen_procs: Set[Tuple[int, float]] = set()
        self._seen_lock = threading.Lock()

        self._platform: str = platform.system()  # 'Windows' | 'Linux' | 'Darwin'

        ProcessMonitor._initialized = True

    # -------------------------------------------------------------------------
    # 生命周期
    # -------------------------------------------------------------------------

    def start(self) -> dict:
        """
        启动进程监控器。

        - 若 PROCESS_MONITOR_ENABLED=False，直接返回（不报错）
        - 若 psutil 未安装，记录警告并返回
        - 否则启动后台扫描线程
        """
        if not PROCESS_MONITOR_ENABLED:
            logger.info("[ProcessMonitor] 已禁用（process_monitor.enabled=false），跳过启动")
            return {"enabled": False, "running": False}

        if not _PSUTIL_OK:
            logger.warning(
                "[ProcessMonitor] psutil 未安装，进程监控不可用。"
                "请执行: pip install psutil"
            )
            return {"enabled": True, "running": False, "error": "psutil not available"}

        if self._running:
            return self.get_status()

        self._running = True
        self._stop_event.clear()

        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            name="ProcessMonitorThread",
            daemon=True,
        )
        self._scan_thread.start()

        logger.info(
            f"[ProcessMonitor] 已启动（平台: {self._platform}，"
            f"扫描间隔: {PROCESS_MONITOR_SCAN_INTERVAL}秒，"
            f"规则数: {len(_PROC_RULES)}）"
        )
        return self.get_status()

    def stop(self) -> None:
        """停止进程监控器，等待扫描线程退出（最多 5 秒）。"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=5)

        logger.info("[ProcessMonitor] 已停止")

    def get_status(self) -> dict:
        """返回当前运行状态摘要。"""
        with self._events_lock:
            pending = len(self._pending_events)
        with self._seen_lock:
            seen = len(self._seen_procs)
        return {
            "enabled":        PROCESS_MONITOR_ENABLED,
            "running":        self._running,
            "psutil_ok":      _PSUTIL_OK,
            "pending_events": pending,
            "seen_procs":     seen,
        }

    def get_recent_events(self, max_count: int = 100) -> List[dict]:
        """
        取出并清空待上报事件队列，返回序列化后的字典列表。
        由 TrafficCollector 的上报线程定期调用。
        """
        with self._events_lock:
            events = self._pending_events[:max_count]
            self._pending_events = self._pending_events[max_count:]
        return [e.to_dict() for e in events]

    # -------------------------------------------------------------------------
    # 扫描主循环
    # -------------------------------------------------------------------------

    def _scan_loop(self) -> None:
        """后台线程：每隔 PROCESS_MONITOR_SCAN_INTERVAL 秒执行一次进程扫描。"""
        cleanup_counter = 0
        while not self._stop_event.is_set():
            try:
                self._scan_processes()
                cleanup_counter += 1
                # 每 12 次扫描（约 1 分钟）清理一次已退出进程的记录
                if cleanup_counter >= 12:
                    cleanup_counter = 0
                    self._cleanup_stale()
            except Exception as exc:
                logger.error(f"[ProcessMonitor] 扫描异常: {exc}")

            self._stop_event.wait(PROCESS_MONITOR_SCAN_INTERVAL)

    def _scan_processes(self) -> None:
        """
        扫描当前运行的所有进程，对未曾分析的进程执行三类检测。
        已分析过的进程（同 pid + create_time）跳过，避免重复分析。
        """
        if not _PSUTIL_OK:
            return

        try:
            # 一次性构建 pid -> proc 映射，减少后续重复访问
            proc_map: Dict[int, "psutil.Process"] = {}
            for proc in psutil.process_iter(
                ["pid", "name", "cmdline", "ppid", "create_time", "status"]
            ):
                try:
                    if proc.status() == psutil.STATUS_ZOMBIE:
                        continue
                    proc_map[proc.pid] = proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as exc:
            logger.debug(f"[ProcessMonitor] 进程列表获取失败: {exc}")
            return

        now = time.time()

        for pid, proc in proc_map.items():
            try:
                create_time = proc.create_time()
                proc_key = (pid, create_time)

                # 已分析过，跳过
                with self._seen_lock:
                    if proc_key in self._seen_procs:
                        continue
                    self._seen_procs.add(proc_key)

                proc_name = _norm_name(proc.name() or "")
                cmdline_list = proc.cmdline() or []
                cmdline = " ".join(str(c) for c in cmdline_list)

                if not cmdline:
                    continue

                # 父进程名
                parent_name = ""
                ppid = proc.ppid()
                if ppid and ppid in proc_map:
                    parent_name = _norm_name(proc_map[ppid].name() or "")

                # ── 检测 1：Web 服务器异常子进程 ─────────────────────────────
                for ev in self._check_web_server_child(
                    pid, proc_name, cmdline, parent_name, now
                ):
                    self._add_event(ev)

                # ── 检测 2：命令行攻击特征匹配 ────────────────────────────────
                for ev in self._check_cmdline_patterns(
                    pid, proc_name, cmdline, parent_name, now
                ):
                    self._add_event(ev)

                # ── 检测 3：敏感文件打开（Linux/macOS 的 Web 进程）──────────
                if (self._platform in ("Linux", "Darwin")
                        and parent_name in _WEB_SERVER_NAMES):
                    for ev in self._check_open_files(
                        pid, proc_name, cmdline, parent_name, proc, now
                    ):
                        self._add_event(ev)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            except Exception as exc:
                logger.debug(f"[ProcessMonitor] 进程 {pid} 分析异常: {exc}")

    # -------------------------------------------------------------------------
    # 检测方法
    # -------------------------------------------------------------------------

    def _check_web_server_child(
        self,
        pid: int,
        proc_name: str,
        cmdline: str,
        parent_name: str,
        now: float,
    ) -> List[ProcessAttackEvent]:
        """
        检测 Web 服务器是否派生了可疑子进程。

        判定逻辑:
            - 父进程是已知 Web 服务器
            - 子进程是 Shell / 网络工具 / 下载工具
            - 对 bash/sh 进一步检查命令行（-c 参数或交互模式），减少误报
        """
        if not parent_name or parent_name not in _WEB_SERVER_NAMES:
            return []
        if proc_name not in _SUSPICIOUS_CHILD_NAMES:
            return []

        # Shell 进程额外过滤：无参数或有 -c/-i 参数才报告，普通脚本执行不报
        if proc_name in ("bash", "sh", "dash", "zsh", "ksh", "csh", "tcsh", "fish"):
            cmdline_lower = cmdline.lower()
            has_suspicious_flag = (
                " -c " in cmdline_lower
                or " -i " in cmdline_lower
                or ">&" in cmdline
                or "/dev/tcp/" in cmdline
            )
            if not has_suspicious_flag and len(cmdline.split()) > 2:
                return []  # 普通脚本，误报风险高，跳过

        # 确定告警级别
        if proc_name in ("nc", "ncat", "netcat", "socat"):
            level = ATTACK_LEVEL_HIGH
            desc = f"Web服务器({parent_name})派生网络工具({proc_name})，疑似反弹Shell"
        elif proc_name in ("cmd", "powershell", "pwsh"):
            level = ATTACK_LEVEL_HIGH
            desc = f"Web服务器({parent_name})派生Windows命令解释器({proc_name})"
        else:
            level = ATTACK_LEVEL_HIGH
            desc = f"Web服务器({parent_name})异常派生Shell进程({proc_name})"

        if not self._check_cooldown(pid, ATTACK_TYPE_CMD_INJECTION, now):
            return []

        return [ProcessAttackEvent(
            attack_type=ATTACK_TYPE_CMD_INJECTION,
            pid=pid,
            process_name=proc_name,
            cmdline=cmdline[:500],
            parent_name=parent_name,
            matched_pattern=desc,
            timestamp=now,
            level=level,
        )]

    def _check_cmdline_patterns(
        self,
        pid: int,
        proc_name: str,
        cmdline: str,
        parent_name: str,
        now: float,
    ) -> List[ProcessAttackEvent]:
        """
        逐条规则匹配进程命令行。
        同一进程同一攻击类型只取第一条命中规则，防止多规则重复告警。
        """
        events: List[ProcessAttackEvent] = []
        hit_types: Set[str] = set()

        for rule in _PROC_RULES:
            if rule.attack_type in hit_types:
                continue  # 该类型已命中，跳过后续同类规则
            if not rule.pattern.search(cmdline):
                continue
            if not self._check_cooldown(pid, rule.attack_type, now):
                hit_types.add(rule.attack_type)
                continue

            events.append(ProcessAttackEvent(
                attack_type=rule.attack_type,
                pid=pid,
                process_name=proc_name,
                cmdline=cmdline[:500],
                parent_name=parent_name,
                matched_pattern=rule.desc,
                timestamp=now,
                level=rule.level,
            ))
            hit_types.add(rule.attack_type)

        return events

    def _check_open_files(
        self,
        pid: int,
        proc_name: str,
        cmdline: str,
        parent_name: str,
        proc: "psutil.Process",
        now: float,
    ) -> List[ProcessAttackEvent]:
        """
        检查 Web 服务进程是否打开了敏感文件（Linux/macOS）。
        每个进程每类攻击只报告第一个命中的敏感文件，避免同一进程批量告警。
        """
        events: List[ProcessAttackEvent] = []
        try:
            open_files = proc.open_files()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return events

        for finfo in open_files:
            path = finfo.path if hasattr(finfo, "path") else str(finfo)
            if not _SENSITIVE_FILE_RE.search(path):
                continue
            if not self._check_cooldown(pid, ATTACK_TYPE_DIR_TRAVERSAL, now):
                break

            events.append(ProcessAttackEvent(
                attack_type=ATTACK_TYPE_DIR_TRAVERSAL,
                pid=pid,
                process_name=proc_name,
                cmdline=f"[open_file] {path}",
                parent_name=parent_name,
                matched_pattern=f"Web进程({proc_name})打开敏感文件: {path}",
                timestamp=now,
                level=ATTACK_LEVEL_HIGH,
            ))
            break  # 同一进程只报一条文件访问告警
        return events

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------

    def _add_event(self, event: ProcessAttackEvent) -> None:
        """将事件写入待上报缓存并输出告警日志。"""
        with self._events_lock:
            self._pending_events.append(event)
            # 防止内存无限增长
            if len(self._pending_events) > 500:
                self._pending_events = self._pending_events[-500:]

        logger.warning(
            f"[ProcessMonitor] 攻击告警 | 类型={event.attack_type} "
            f"进程={event.process_name}(pid={event.pid}) "
            f"父进程={event.parent_name or 'unknown'} "
            f"特征={event.matched_pattern} "
            f"等级={event.level}"
        )

    def _check_cooldown(self, pid: int, attack_type: str, now: float) -> bool:
        """
        检查冷却期。
        返回 True 表示可以告警（冷却已过），同时更新时间戳；
        返回 False 表示仍在冷却期。
        """
        key = (pid, attack_type)
        with self._cooldown_lock:
            if now - self._cooldown.get(key, 0.0) < PROCESS_MONITOR_COOLDOWN:
                return False
            self._cooldown[key] = now
        return True

    def _cleanup_stale(self) -> None:
        """
        清理已退出进程的记录（seen_procs、cooldown），防止内存无限增长。
        约每分钟调用一次。
        """
        if not _PSUTIL_OK:
            return
        try:
            alive_pids: Set[int] = set(psutil.pids())

            with self._seen_lock:
                self._seen_procs = {
                    (pid, ct) for pid, ct in self._seen_procs
                    if pid in alive_pids
                }
                # 安全上限：超过 20000 条时保留最近记录
                if len(self._seen_procs) > 20000:
                    self._seen_procs = set(
                        sorted(self._seen_procs, key=lambda x: x[1])[-10000:]
                    )

            with self._cooldown_lock:
                stale_keys = [
                    k for k in self._cooldown if k[0] not in alive_pids
                ]
                for k in stale_keys:
                    del self._cooldown[k]
        except Exception:
            pass


# =============================================================================
# 内部工具函数
# =============================================================================

def _norm_name(name: str) -> str:
    """标准化进程名：去掉路径前缀，去掉 .exe 后缀，转小写。"""
    base = os.path.basename(name).lower()
    if base.endswith(".exe"):
        base = base[:-4]
    return base


# =============================================================================
# 全局单例
# =============================================================================

process_monitor = ProcessMonitor()
