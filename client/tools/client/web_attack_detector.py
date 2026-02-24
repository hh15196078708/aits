# -*- coding: utf-8 -*-
"""
模块名称: web_attack_detector.py
模块功能: 检测常见Web应用攻击行为（SQL注入、XSS、目录遍历、命令注入、CSRF、远程代码执行）
依赖模块:
    - 标准库: threading, time, re, os, platform, collections, urllib.parse
    - config_manager: 读取可配置的日志源列表
系统适配: Windows (IIS) / Linux (Apache/Nginx/Tomcat) / macOS

检测方法:
    1. Web日志分析法（主要方法）:
       - 增量读取Web服务器访问日志，对请求URI和参数进行特征匹配
       - 支持日志类型: nginx | apache | iis | tomcat | auto
       - 日志源优先从 config_manager 读取配置，若未配置则自动发现系统默认路径
       - 支持文件路径和目录路径两种配置方式

日志源配置（存储于 client_config.json 的 web_log_sources 字段）:
    [
        {"path": "/var/log/nginx/access.log",      "type": "nginx",  "enabled": true},
        {"path": "/var/log/apache2/access.log",    "type": "apache", "enabled": true},
        {"path": "/opt/tomcat/logs",               "type": "tomcat", "enabled": true},
        {"path": "C:\\inetpub\\logs\\LogFiles",    "type": "iis",    "enabled": true},
        {"path": "/var/log/httpd/access_log",      "type": "auto",   "enabled": true}
    ]

    - path: 文件路径或目录路径
      * 文件路径: 直接读取该文件（nginx/apache/iis/tomcat 单个日志文件）
      * 目录路径: 自动扫描目录下匹配的日志文件（适合IIS和Tomcat按日期轮转的场景）
    - type: 日志格式类型
      * nginx:  Nginx Combined Log Format，使用Apache解析器
      * apache: Apache Combined Log Format
      * iis:    IIS W3C Extended Log Format
      * tomcat: Tomcat AccessLogValve（Common/Combined格式），使用Apache解析器
      * auto:   根据路径特征自动判断类型
    - enabled: 是否启用该日志源，false时跳过

热更新机制:
    每隔 CONFIG_RELOAD_INTERVAL（默认300秒）自动从 config_manager 重新读取日志源配置，
    无需重启程序即可生效新增/修改/删除的日志源。
    也可通过调用 web_attack_detector.reload_log_sources() 立即生效。

检测规则:
    - SQL注入:   UNION SELECT、条件注入、时间盲注、DDL截断、系统存储过程等
    - XSS攻击:   <script>标签、javascript:协议、内联事件处理器、DOM操作函数等
    - 目录遍历:  ../及其URL编码、双重编码、Unicode编码变体，敏感系统文件路径
    - 命令注入:  Shell分隔符+系统命令、命令替换语法、管道命令、反弹Shell
    - CSRF:      状态变更请求（POST/PUT/DELETE/PATCH）且缺少Referer头的敏感API访问
    - 远程代码执行: 代码执行函数、危险流包装器、模板注入（SSTI）、反序列化、Log4Shell

冷却机制:
    - 同一IP同一攻击类型，60秒内不重复告警（防止告警风暴）
    - 每10次轮询执行一次过期冷却记录清理
"""

import os
import re
import time
import platform
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Tuple
from urllib.parse import unquote

from constants import (
    ATTACK_TYPE_SQL_INJECTION,
    ATTACK_TYPE_XSS,
    ATTACK_TYPE_DIR_TRAVERSAL,
    ATTACK_TYPE_CMD_INJECTION,
    ATTACK_TYPE_CSRF,
    ATTACK_TYPE_RCE,
    ATTACK_LEVEL_HIGH,
    ATTACK_LEVEL_MEDIUM,
    DEFAULT_THRESHOLDS,
)
from logger import logger


# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------

# 日志源配置热更新间隔（每N次轮询重新读取一次config_manager）
_CONFIG_RELOAD_CYCLES = 30  # 30次 × 10秒/次 = 300秒（5分钟）

# 日志读取偏移量持久化间隔（每N次轮询保存一次）
_OFFSET_SAVE_CYCLES = 6     # 6次 × 10秒/次 = 60秒

# 首次读取日志时，最多读取末尾大小（字节，避免解析大量历史日志）
_LOG_TAIL_SIZE = int(DEFAULT_THRESHOLDS.get("web_attack_log_tail_size", 65536))


# ---------------------------------------------------------------------------
# 攻击特征正则模式库
# ---------------------------------------------------------------------------

# SQL注入特征模式
_SQL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"union\s+(all\s+)?select", re.IGNORECASE),
     "UNION SELECT注入"),
    (re.compile(r"(\s|'|\"|%27|%22)(or|and)\s+['\"%\d]*\d+['\"%\d]*\s*=\s*['\"%\d]*\d+", re.IGNORECASE),
     "布尔条件注入(OR/AND永真式)"),
    (re.compile(r"(?:'[^']*|\"[^\"]*|\b\d+)\s*(?:--|/\*)", re.IGNORECASE),
     "SQL注释截断(含值上下文)"),
    (re.compile(r";\s*(drop|truncate|delete|insert|update)\s+", re.IGNORECASE),
     "危险DDL/DML语句注入"),
    (re.compile(r"(sleep\s*\(\s*\d+|waitfor\s+delay\s+['\"])", re.IGNORECASE),
     "时间盲注"),
    (re.compile(r"(@@version|@@hostname|@@datadir|information_schema|sys\.databases|sysobjects)", re.IGNORECASE),
     "数据库信息泄露函数"),
    (re.compile(r"(xp_cmdshell|sp_executesql|exec\s*\(|execute\s*\()", re.IGNORECASE),
     "危险存储过程调用"),
    (re.compile(r"(load_file\s*\(|into\s+outfile|into\s+dumpfile)", re.IGNORECASE),
     "文件读写注入"),
    (re.compile(r"(char\s*\(\s*\d+|ascii\s*\(|substring\s*\(|mid\s*\(|ord\s*\()", re.IGNORECASE),
     "盲注辅助函数"),
    (re.compile(r"'[^']*'\s*(=|<|>|like)\s*'[^']*'\s*(or|and)", re.IGNORECASE),
     "字符串比较注入"),
]

# XSS攻击特征模式
_XSS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"<\s*script[\s>/]", re.IGNORECASE),
     "<script>标签注入"),
    (re.compile(r"</\s*script\s*>", re.IGNORECASE),
     "</script>闭合标签"),
    (re.compile(r"javascript\s*:", re.IGNORECASE),
     "javascript:协议"),
    (re.compile(r"\bon\w+\s*=\s*['\"]?\s*(alert|confirm|prompt|eval|document|window|location|fetch)", re.IGNORECASE),
     "HTML内联事件处理器"),
    (re.compile(r"<\s*(iframe|object|embed|applet|base|form|link)\s", re.IGNORECASE),
     "危险HTML标签注入"),
    (re.compile(r"document\s*\.\s*(cookie|write|location|domain|body|createElement)", re.IGNORECASE),
     "DOM操作攻击"),
    (re.compile(r"(expression\s*\(|vbscript\s*:)", re.IGNORECASE),
     "CSS/VBScript注入"),
    (re.compile(r"data:\s*text/(html|javascript)", re.IGNORECASE),
     "data:URI XSS"),
    (re.compile(r"<\s*svg\s[^>]*(onload|onerror|onmouseover)\s*=", re.IGNORECASE),
     "SVG事件注入"),
    (re.compile(r"(%3c|&lt;|&#60;|&#x3c;).{0,20}(script|iframe|alert)", re.IGNORECASE),
     "HTML实体编码绕过XSS"),
]

# 目录遍历特征模式
_DIR_TRAVERSAL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(\.\.[/\\]){2,}", re.IGNORECASE),
     "多层路径遍历（../../）"),
    (re.compile(r"(%2e%2e%2f|%2e%2e/|\.\.%2f|%2e%2e%5c)", re.IGNORECASE),
     "URL编码路径遍历"),
    (re.compile(r"(%252e%252e|%252f|%255c)", re.IGNORECASE),
     "双重URL编码路径遍历"),
    (re.compile(r"(\.\.%c0%af|\.\.%c1%9c|%c0%ae%c0%ae)", re.IGNORECASE),
     "Unicode编码路径遍历"),
    (re.compile(r"\.\.[/\\].*(etc/passwd|etc/shadow|etc/hosts|windows[/\\]win\.ini|boot\.ini|system32[/\\]drivers)", re.IGNORECASE),
     "敏感系统文件读取"),
    (re.compile(r"(\.\.[/\\]){3,}", re.IGNORECASE),
     "深层路径回溯（3级以上）"),
    (re.compile(r"(proc/self/environ|proc/self/cmdline|proc/version)", re.IGNORECASE),
     "/proc敏感文件访问"),
    # ── 补充规则：编码变体与高价值目标 ──────────────────────────────────────────
    (re.compile(r"\.\.%5c|\.\.%5C", re.IGNORECASE),
     "URL编码反斜杠路径遍历(..%5c)"),
    (re.compile(r"\.%2e/|%2e\./|\.%2e\\|%2e\.\\", re.IGNORECASE),
     "混合点编码路径遍历(.%2e/)"),
    (re.compile(r"\.\.[/\\].*(\.htaccess|\.htpasswd|\.ssh[/\\]|authorized_keys|id_rsa\b|id_dsa\b|id_ed25519\b)", re.IGNORECASE),
     "SSH凭证/用户鉴权文件遍历"),
    (re.compile(r"\.\.[/\\].*(WEB-INF|META-INF)[/\\]", re.IGNORECASE),
     "Java Web应用目录遍历(WEB-INF/META-INF)"),
    (re.compile(r"\.\.[/\\].*(wp-config\.php|web\.config|\.env\b|database\.yml|application\.properties|settings\.py|config\.php)", re.IGNORECASE),
     "Web应用敏感配置文件遍历"),
    (re.compile(r"%00\s*\.[a-zA-Z]{2,5}(?:\s|$|&|#)", re.IGNORECASE),
     "空字节截断绕过文件扩展名"),
    (re.compile(r"file://+/?(?:[a-zA-Z]:|/)", re.IGNORECASE),
     "file://协议本地文件读取"),
    (re.compile(r"(?:/\./|(?:[^/]+/)+\.\./){2,}", re.IGNORECASE),
     "路径规范化绕过遍历"),
]

# 命令注入特征模式
_CMD_INJECTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"[;&|`]\s*(ls|cat|id|whoami|uname|pwd|echo|curl|wget|bash|sh|python|perl|php|ruby)\b", re.IGNORECASE),
     "Shell分隔符+系统命令"),
    (re.compile(r"(\$\(|\`)\s*(id|whoami|ls|cat|uname|hostname|ifconfig|ipconfig)\s*(\)|\`)", re.IGNORECASE),
     "命令替换注入"),
    (re.compile(r"\|\s*(bash|sh|cmd\.exe|powershell|nc|ncat|netcat)\b", re.IGNORECASE),
     "管道命令注入"),
    (re.compile(r"(%0a|%0d|%00)\s*(dir|type|ping|ipconfig|whoami|cat|ls)", re.IGNORECASE),
     "换行/空字节命令注入"),
    (re.compile(r";\s*(sleep|ping)\s+\d+", re.IGNORECASE),
     "时间延迟命令注入"),
    (re.compile(r"(bash\s+-i\s+>&|nc\s+.*-e\s+|/dev/tcp/\d)", re.IGNORECASE),
     "反弹Shell特征"),
    (re.compile(r"(nslookup|dig)\s+\S+\s*[;&|]", re.IGNORECASE),
     "DNS外带命令注入"),
    (re.compile(r"&&\s*(id|whoami|ls|cat|dir|type)\b", re.IGNORECASE),
     "逻辑与命令链注入"),
    # ── 补充规则：PowerShell / LOLBins / 现代攻击技术 ────────────────────────────
    (re.compile(r"powershell(?:\.exe)?\s+(?:.*-(?:[eE]nc(?:odedcommand)?|[eE][cC])\s+[A-Za-z0-9+/=]{16,}|.*-[eE]xecution[pP]olicy\s+[bB]ypass|.*-[wW]indow[sS]tyle\s+[hH]idden)", re.IGNORECASE),
     "PowerShell绕过执行策略或编码命令"),
    (re.compile(r"(?:IEX|Invoke-Expression|Invoke-WebRequest)\s*\(?|(?:DownloadString|DownloadFile)\s*\(", re.IGNORECASE),
     "PowerShell远程代码下载执行"),
    (re.compile(r"(?:certutil|bitsadmin|mshta|regsvr32|rundll32|msiexec)\s+(?:-\w+\s+)*(?:https?://|ftp://|/transfer|/execute|/urlcache)", re.IGNORECASE),
     "Windows LOLBins文件下载或执行"),
    (re.compile(r"\$\{IFS\}|\$IFS(?:\s|$|;)|%09(?=.*(?:ls|cat|id|whoami))", re.IGNORECASE),
     "IFS环境变量或制表符注入绕过空格过滤"),
    (re.compile(r"[;&|`]\s*(?:chmod\s+(?:[0-9]{4}|\+s|u\+s)|chown\s+root)", re.IGNORECASE),
     "SUID/权限提升命令注入"),
    (re.compile(r"[;&|`]\s*(?:wget|curl)\s+\S+\s*\|\s*(?:ba)?sh", re.IGNORECASE),
     "下载并管道执行恶意脚本"),
    (re.compile(r"[;&|`]\s*(?:mkfifo|mknod)\s+\S+", re.IGNORECASE),
     "创建命名管道(疑似反弹Shell)"),
    (re.compile(r">\s*/(?:etc/cron\.|tmp/|var/spool/cron/|dev/tcp/)", re.IGNORECASE),
     "重定向写入系统关键目录(定时任务/反弹)"),
]

# CSRF检测辅助配置（基于字段逻辑判断）
_CSRF_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

# 敏感API路径（仅保留真正高风险的状态变更接口）
# 移除 login/logout/register/auth：这类接口的 POST 请求天然无 Referer，误报率极高
_CSRF_SENSITIVE_PATH_PATTERN = re.compile(
    r"/(api|admin|account|payment|transfer|password|passwd|profile|"
    r"setting|config|order|withdraw|upload)/",
    re.IGNORECASE,
)

# 浏览器 User-Agent 特征：CSRF 必须由受害者浏览器发起，非浏览器 UA 不可能是 CSRF
# 包含 Mozilla/ 的 UA 基本覆盖所有主流浏览器（Chrome/Firefox/Safari/Edge/IE）
_BROWSER_UA_PATTERN = re.compile(
    r"mozilla/\d|chrome/\d|safari/\d|firefox/\d|trident/|edge/",
    re.IGNORECASE,
)

# 远程代码执行特征模式
_RCE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(eval|assert|preg_replace)\s*\(", re.IGNORECASE),
     "PHP代码执行函数"),
    (re.compile(r"(system|passthru|shell_exec|popen|proc_open)\s*\(", re.IGNORECASE),
     "PHP系统命令执行函数"),
    (re.compile(r"(php://input|php://filter|php://data)", re.IGNORECASE),
     "PHP流包装器"),
    (re.compile(r"(data://text/plain|expect://|zip://|phar://)", re.IGNORECASE),
     "危险URI流包装器"),
    (re.compile(r"(\{\{.*?\}\}|\$\{[^}]+\}|#\{[^}]+\})", re.IGNORECASE),
     "模板注入（SSTI）"),
    (re.compile(r"(__class__|__import__|__builtins__|__globals__|__subclasses__)", re.IGNORECASE),
     "Python对象属性注入"),
    (re.compile(r"(include|require|include_once|require_once)\s*\(['\"]?(https?://|ftp://|//)", re.IGNORECASE),
     "远程文件包含（RFI）"),
    (re.compile(r"O:\d+:\"[A-Za-z_][A-Za-z0-9_]*\":\d+:\{", re.IGNORECASE),
     "PHP反序列化攻击"),
    (re.compile(r"(Runtime\.exec|ProcessBuilder|ScriptEngine|GroovyShell)", re.IGNORECASE),
     "Java代码执行"),
    (re.compile(r"\$\{(j|J)ndi:(ldap|rmi|dns|corba|iiop|http)://", re.IGNORECASE),
     "Log4Shell JNDI注入（CVE-2021-44228）"),
]

# 攻击类型 -> 威胁等级映射
_ATTACK_LEVEL_MAP: Dict[str, str] = {
    ATTACK_TYPE_SQL_INJECTION: ATTACK_LEVEL_HIGH,
    ATTACK_TYPE_XSS:           ATTACK_LEVEL_MEDIUM,
    ATTACK_TYPE_DIR_TRAVERSAL: ATTACK_LEVEL_MEDIUM,
    ATTACK_TYPE_CMD_INJECTION: ATTACK_LEVEL_HIGH,
    ATTACK_TYPE_CSRF:          ATTACK_LEVEL_MEDIUM,
    ATTACK_TYPE_RCE:           ATTACK_LEVEL_HIGH,
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class WebAttackEvent:
    """Web攻击事件，包含检测结果的完整信息"""
    attack_type: str        # 攻击类型（对应 ATTACK_TYPE_* 常量）
    source_ip: str          # 攻击来源IP
    request_uri: str        # 攻击请求URI（截断至500字符）
    request_method: str     # HTTP请求方法（GET/POST/PUT/DELETE等）
    matched_pattern: str    # 命中的特征描述
    timestamp: float        # 检测时间戳（Unix时间）
    level: str              # 威胁等级: low / medium / high
    detection_method: str   # 检测方式: log
    user_agent: str = ""    # User-Agent（可选）
    referer: str = ""       # Referer（可选）

    def to_dict(self) -> dict:
        """序列化为可上报的字典"""
        return {
            # ── 公共字段 ──────────────────────────────────────────────────────
            "attack_type":      self.attack_type,
            "source_ip":        self.source_ip,
            "request_uri":      self.request_uri[:500],
            "request_method":   self.request_method,
            "matched_pattern":  self.matched_pattern,
            "timestamp":        self.timestamp,
            "level":            self.level,
            "detection_method": self.detection_method,
            # ── Web 专属 ──────────────────────────────────────────────────────
            "user_agent":       self.user_agent[:200] if self.user_agent else "",
            "referer":          self.referer[:200] if self.referer else "",
            # ── Payload 专属（日志检测不适用，填空占位保持结构一致）────────────
            "dest_port":        None,
            "protocol":         "",
            "payload_snippet":  "",
        }


# ---------------------------------------------------------------------------
# Web服务器日志解析器
# ---------------------------------------------------------------------------

class WebLogParser:
    """
    Web服务器访问日志行解析器

    支持格式:
        1. Apache/Nginx/Tomcat Combined Log Format:
           ip - - [时间] "METHOD /path HTTP/1.1" status size "referer" "user-agent"
           （referer 和 user-agent 为可选字段，Tomcat Common格式不含这两项）

        2. IIS W3C Extended Log Format:
           date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip
           [cs(User-Agent) cs(Referer) sc-status ...]
    """

    # Apache/Nginx/Tomcat Combined Log 正则（referer 和 user-agent 均为可选）
    # 示例（Combined）: 1.2.3.4 - - [01/Jan/2024:12:00:00 +0800] "GET /index.php?id=1 HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
    # 示例（Common）:   1.2.3.4 - - [01/Jan/2024:12:00:00 +0800] "GET /index.jsp HTTP/1.1" 200 1234
    _APACHE_RE = re.compile(
        r'^(\S+)'              # client_ip
        r'\s+\S+\s+\S+\s+'    # ident, authuser
        r'\[[^\]]+\]\s+'       # [time]
        r'"(\S+)\s+(\S*)'      # "METHOD URI
        r'[^"]*"\s+'           # HTTP/x.x"
        r'(\d+)\s+'            # status
        r'\S+'                 # size
        r'(?:\s+"([^"]*)")?'   # "referer" (optional)
        r'(?:\s+"([^"]*)")?'   # "user-agent" (optional)
    )

    # IIS W3C Log 正则
    # 字段顺序: date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip [cs(User-Agent) cs(Referer) ...]
    # 示例: 2024-01-01 12:00:00 192.168.1.1 GET /index.aspx ?id=1 80 - 10.0.0.1 Mozilla/5.0 http://example.com 200
    _IIS_RE = re.compile(
        r'^\d{4}-\d{2}-\d{2}\s+'   # date
        r'\d{2}:\d{2}:\d{2}\s+'    # time
        r'\S+\s+'                   # s-ip
        r'(\S+)\s+'                 # cs-method
        r'(\S+)\s+'                 # cs-uri-stem
        r'(\S+)\s+'                 # cs-uri-query
        r'\S+\s+'                   # s-port
        r'\S+\s+'                   # cs-username
        r'(\S+)'                    # c-ip
        r'(?:\s+(\S+))?'            # cs(User-Agent) (optional)
        r'(?:\s+(\S+))?'            # cs(Referer) (optional)
    )

    @classmethod
    def parse_apache(cls, line: str) -> Optional[dict]:
        """
        解析 Apache/Nginx/Tomcat Combined（或Common）日志行。
        成功返回请求字段字典，解析失败返回 None。
        """
        m = cls._APACHE_RE.match(line.strip())
        if not m:
            return None
        client_ip, method, uri, status, referer, user_agent = m.groups()
        try:
            uri_decoded = _multi_decode(uri or "")
        except Exception:
            uri_decoded = uri or ""
        return {
            "source_ip":   client_ip or "",
            "method":      (method or "GET").upper(),
            "uri":         uri_decoded,
            "raw_uri":     uri or "",
            "status_code": int(status) if status and status.isdigit() else 0,
            "referer":     referer or "",
            "user_agent":  user_agent or "",
        }

    @classmethod
    def parse_iis(cls, line: str) -> Optional[dict]:
        """
        解析 IIS W3C 格式日志行。
        跳过 # 开头的注释行（IIS日志头部字段描述行）。
        成功返回请求字段字典，解析失败返回 None。
        """
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return None
        m = cls._IIS_RE.match(stripped)
        if not m:
            return None
        method, uri_stem, uri_query, client_ip, user_agent, referer = m.groups()
        uri_stem = uri_stem or "/"
        if uri_query and uri_query != "-":
            try:
                uri = f"{uri_stem}?{_multi_decode(uri_query)}"
            except Exception:
                uri = f"{uri_stem}?{uri_query}"
        else:
            uri = uri_stem
        return {
            "source_ip":   client_ip or "",
            "method":      (method or "GET").upper(),
            "uri":         uri,
            "raw_uri":     uri,
            "status_code": 0,
            "referer":     referer or "",
            "user_agent":  user_agent or "",
        }


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _multi_decode(uri: str) -> str:
    """
    对URI进行多重URL解码（最多3层），防止编码绕过攻击。
    例如 %2527 → %27 → '
    """
    result = uri
    for _ in range(3):
        try:
            decoded = unquote(result)
            if decoded == result:
                break
            result = decoded
        except Exception:
            break
    return result


# ---------------------------------------------------------------------------
# 日志源解析辅助函数
# ---------------------------------------------------------------------------

# 各平台Web服务器日志自动发现候选路径（未配置时的回退）
_DEFAULT_LOG_CANDIDATES: Dict[str, List[Tuple[str, str]]] = {
    "Linux": [
        # Nginx
        ("/var/log/nginx/access.log",              "nginx"),
        ("/var/log/nginx/access_log",              "nginx"),
        # Apache
        ("/var/log/apache2/access.log",            "apache"),
        ("/var/log/apache2/access_log",            "apache"),
        ("/var/log/httpd/access_log",              "apache"),
        ("/var/log/httpd/access.log",              "apache"),
        # Tomcat（常见安装路径，按目录匹配）
        ("/var/log/tomcat/",                       "tomcat"),
        ("/var/log/tomcat8/",                      "tomcat"),
        ("/var/log/tomcat9/",                      "tomcat"),
        ("/var/log/tomcat10/",                     "tomcat"),
        ("/opt/tomcat/logs/",                      "tomcat"),
        ("/opt/apache-tomcat/logs/",               "tomcat"),
        ("/usr/share/tomcat/logs/",                "tomcat"),
        ("/usr/local/tomcat/logs/",                "tomcat"),
    ],
    "Darwin": [
        # Apache（macOS自带 / Homebrew）
        ("/var/log/apache2/access_log",            "apache"),
        ("/usr/local/var/log/httpd/access_log",    "apache"),
        # Nginx（Homebrew）
        ("/usr/local/var/log/nginx/access.log",    "nginx"),
        ("/opt/homebrew/var/log/nginx/access.log", "nginx"),
        # Tomcat（Homebrew）
        ("/usr/local/opt/tomcat/logs/",            "tomcat"),
    ],
    # Windows：IIS 和 Tomcat 目录，在 _scan_log_dir 中动态展开
    "Windows": [
        (r"C:\inetpub\logs\LogFiles",              "iis"),
        (r"D:\inetpub\logs\LogFiles",              "iis"),
        (r"C:\Program Files\Apache Software Foundation\Tomcat 10.1\logs", "tomcat"),
        (r"C:\Program Files\Apache Software Foundation\Tomcat 9.0\logs",  "tomcat"),
        (r"C:\tomcat\logs",                        "tomcat"),
    ],
}

# Tomcat 日志文件名匹配模式（按日期轮转）
_TOMCAT_LOG_RE = re.compile(
    r"^(localhost_access_log|access_log|access[-_]log).*\.(txt|log)$",
    re.IGNORECASE,
)

# IIS 日志文件名匹配模式（u_exYYMMDD.log）
_IIS_LOG_RE = re.compile(r"^u_ex[\d_]+\.log$", re.IGNORECASE)


def _auto_detect_type(path: str) -> str:
    """
    根据路径特征自动判断Web服务器日志类型。
    返回内部解析器类型: 'apache' 或 'iis'。

    优先级:
        1. 路径中包含明确的服务器名称关键字
        2. 文件名匹配 IIS 命名规则（u_exYYMMDD.log）
        3. 兜底：使用 apache 解析器（兼容性最广）
    """
    norm = path.lower().replace("\\", "/")
    fname = os.path.basename(path).lower()

    # IIS 关键字或命名规则
    if "inetpub" in norm or "/w3svc" in norm or _IIS_LOG_RE.match(fname):
        return "iis"
    # Nginx/Apache/Tomcat 均使用 Combined Log Format
    if any(k in norm for k in ("nginx", "apache", "httpd", "tomcat", "catalina", "localhost_access")):
        return "apache"
    # 兜底
    return "apache"


def _resolve_parser_type(server_type: str, path: str) -> str:
    """
    将用户配置的服务器类型映射到内部解析器类型（'apache' 或 'iis'）。

    - nginx / apache / tomcat  ->  'apache'（Combined/Common Log Format 共用解析器）
    - iis                      ->  'iis'
    - auto                     ->  根据路径自动判断
    """
    normalized = server_type.strip().lower()
    if normalized in ("nginx", "apache", "tomcat"):
        return "apache"
    if normalized == "iis":
        return "iis"
    # auto 或未知类型：根据路径自动判断
    return _auto_detect_type(path)


def _scan_log_dir(directory: str, server_type: str) -> List[Tuple[str, str]]:
    """
    扫描目录下匹配的Web服务器日志文件。

    - iis:    递归扫描一层子目录（W3SVC1/u_ex*.log）
    - tomcat: 扫描当前目录匹配 Tomcat 日志命名规则的文件
    - 其他:   扫描当前目录下所有 .log 和 access_log* 文件
    返回 [(文件绝对路径, 解析器类型)] 列表。
    """
    result: List[Tuple[str, str]] = []
    parser_type = _resolve_parser_type(server_type, directory)

    if not os.path.isdir(directory):
        return result

    try:
        if server_type.lower() == "iis":
            # IIS 日志存放在 LogFiles\W3SVC1\ 等子目录中
            for entry in os.scandir(directory):
                if not entry.is_dir():
                    continue
                try:
                    for sub in os.scandir(entry.path):
                        if sub.is_file() and _IIS_LOG_RE.match(sub.name):
                            result.append((sub.path, "iis"))
                except PermissionError:
                    pass
        elif server_type.lower() == "tomcat":
            # Tomcat 日志按日期命名在同一目录下
            for entry in os.scandir(directory):
                if entry.is_file() and _TOMCAT_LOG_RE.match(entry.name):
                    result.append((entry.path, "apache"))
        else:
            # Nginx / Apache / auto：扫描当前目录下常见日志文件
            for entry in os.scandir(directory):
                if not entry.is_file():
                    continue
                name_lower = entry.name.lower()
                if name_lower.endswith(".log") or name_lower.startswith("access"):
                    result.append((entry.path, parser_type))
    except PermissionError:
        logger.debug(f"无权限扫描日志目录: {directory}")
    except Exception as e:
        logger.debug(f"扫描日志目录异常 [{directory}]: {e}")

    return result


# ---------------------------------------------------------------------------
# 基于Web日志的攻击检测器
# ---------------------------------------------------------------------------

class LogBasedWebAttackDetector:
    """
    基于Web服务器访问日志的多类型攻击检测器

    增量读取Web日志文件，对每条请求进行SQL注入、XSS、目录遍历、
    命令注入、CSRF和远程代码执行的特征匹配检测。

    日志源优先级:
        1. 通过 update_sources() 设置的可配置日志源（来自 config_manager）
        2. 若无配置，自动发现平台默认日志路径（_DEFAULT_LOG_CANDIDATES）

    特性:
        - 增量读取（维护文件偏移量，不重复解析历史日志）
        - 冷却机制（同IP同类型60秒内不重复告警）
        - 多重URL解码（防止编码绕过）
        - 运行时热更新日志源（调用 update_sources()）
    """

    def __init__(self, cooldown_seconds: float, on_detect: Callable[[WebAttackEvent], None]):
        self._cooldown_seconds = cooldown_seconds
        self._on_detect = on_detect
        self._platform = platform.system()

        # 用户配置的日志源（来自 config_manager），为空时使用平台默认路径
        self._configured_sources: List[dict] = []
        self._sources_lock = threading.Lock()

        # 日志文件读取偏移量，持久化以支持重启后续读
        # key: 文件绝对路径
        # value: {"offset": int, "size": int, "mtime": float, "inode": int}
        #   offset — 下次应从此字节位置开始读取
        #   size   — 上次读取时文件大小（辅助轮转检测）
        #   mtime  — 上次读取时文件修改时间（辅助轮转检测）
        #   inode  — 上次读取时文件inode号（用于删除重建检测）
        #            Unix/macOS: inode号; Windows NTFS: 文件索引号; FAT: 0（不可用）
        self._log_offsets: Dict[str, dict] = {}

        # 冷却期记录（key: "source_ip:attack_type"，value: 上次告警时间戳）
        self._cooldown_map: Dict[str, float] = {}
        self._cooldown_lock = threading.Lock()

    def update_sources(self, sources: List[dict]):
        """
        热更新日志源配置。

        参数 sources 为来自 config_manager.get_web_log_sources() 的列表，
        每项格式: {"path": str, "type": str, "enabled": bool}

        若 sources 为空列表，则回退到自动发现模式。
        """
        with self._sources_lock:
            self._configured_sources = [s for s in sources if isinstance(s, dict)]
        logger.info(f"Web日志源配置已更新，共 {len(self._configured_sources)} 条")

    def check(self) -> List[WebAttackEvent]:
        """执行一次日志扫描，返回本次新发现的攻击事件列表"""
        events: List[WebAttackEvent] = []
        for log_file, parser_type in self._resolve_log_files():
            try:
                file_events = self._scan_log_file(log_file, parser_type)
                events.extend(file_events)
            except PermissionError:
                logger.debug(f"无权限读取日志文件: {log_file}")
            except Exception as e:
                logger.debug(f"读取Web日志文件异常 [{log_file}]: {e}")
        return events

    def cleanup_stale(self):
        """清理过期冷却期记录，防止内存无限增长"""
        now = time.time()
        expire_after = self._cooldown_seconds * 2
        with self._cooldown_lock:
            stale = [k for k, t in self._cooldown_map.items() if now - t > expire_after]
            for k in stale:
                del self._cooldown_map[k]

    # ------------------------------------------------------------------
    # 内部：日志文件解析
    # ------------------------------------------------------------------

    def _resolve_log_files(self) -> List[Tuple[str, str]]:
        """
        解析最终需要扫描的 (文件路径, 解析器类型) 列表。

        优先使用配置的日志源，否则自动发现平台默认路径。
        """
        with self._sources_lock:
            sources = list(self._configured_sources)

        if sources:
            return self._expand_configured_sources(sources)
        return self._auto_discover_log_files()

    def _expand_configured_sources(self, sources: List[dict]) -> List[Tuple[str, str]]:
        """
        将用户配置的日志源列表展开为具体的 (文件路径, 解析器类型) 列表。

        - 若 path 为文件，直接使用
        - 若 path 为目录，调用 _scan_log_dir() 展开为目录内的日志文件
        - enabled 为 false 的项跳过
        """
        result: List[Tuple[str, str]] = []
        for source in sources:
            if not source.get("enabled", True):
                continue
            path = source.get("path", "").strip()
            server_type = source.get("type", "auto").strip().lower()
            if not path:
                continue

            if os.path.isfile(path):
                parser_type = _resolve_parser_type(server_type, path)
                result.append((path, parser_type))
            elif os.path.isdir(path):
                result.extend(_scan_log_dir(path, server_type))
            else:
                logger.debug(f"Web日志路径不存在或不可访问: {path}")
        return result

    def _auto_discover_log_files(self) -> List[Tuple[str, str]]:
        """
        自动发现平台默认Web日志路径（无配置时的回退策略）。
        """
        result: List[Tuple[str, str]] = []
        candidates = _DEFAULT_LOG_CANDIDATES.get(self._platform, [])

        for path, server_type in candidates:
            if os.path.isfile(path):
                parser_type = _resolve_parser_type(server_type, path)
                result.append((path, parser_type))
            elif os.path.isdir(path):
                result.extend(_scan_log_dir(path, server_type))

        return result

    def load_offsets_from_config(self):
        """
        从 config_manager 加载持久化的日志文件读取偏移量。

        在检测器启动时调用，确保重启后从上次处理的位置继续读取，
        避免重复检测已处理过的日志行。
        """
        try:
            from config_manager import config_manager
            stored = config_manager.get_web_log_offsets()
            if stored and isinstance(stored, dict):
                self._log_offsets.update(stored)
                logger.info(f"已恢复 {len(stored)} 个日志文件的读取偏移量（续读模式）")
        except Exception as e:
            logger.warning(f"加载日志偏移量失败，将以末尾64KB作为起点: {e}")

    def save_offsets_to_config(self):
        """
        将当前日志文件读取偏移量持久化到 config_manager。

        定期调用（约每60秒）和停止时调用，确保异常退出后
        重启最多重复处理约60秒的日志，而非全部历史日志。
        同时清理已不存在的文件的偏移量记录，防止配置文件无限膨胀。
        """
        try:
            # 清理已不存在文件的偏移量记录
            valid = {p: info for p, info in self._log_offsets.items()
                     if os.path.exists(p)}
            from config_manager import config_manager
            config_manager.set_web_log_offsets(valid)
        except Exception as e:
            logger.warning(f"保存日志偏移量失败: {e}")

    def _scan_log_file(self, log_file: str, parser_type: str) -> List[WebAttackEvent]:
        """
        增量读取并分析单个日志文件。

        偏移量管理策略（按优先级依次检测）:
            1. 首次读取（无持久化记录）
               → 仅取末尾64KB，跳过历史日志
            2. inode变化（文件被删除后重新创建）
               → 无论新文件大小是否超过旧偏移，均从头读取
               → 适用于: logrotate、运维手动删除后服务重建、
                          Python logging RotatingFileHandler等场景
            3. 文件大小回退（同inode但内容被截断或轮转）
               → 当前大小 < 记录偏移，从头读取
               → 适用于: IIS/Tomcat按日期新建文件、truncate清空等
               → 也作为 Windows FAT(inode=0)下的兄底检测
            4. 正常续读
               → 从上次保存的偏移量继续，无重复处理

        注: inode在 Windows FAT/exFAT 文件系统上可能为0（不可用），
            此时自动降级为大小回退检测（策略3）。
        """
        events: List[WebAttackEvent] = []

        # 单次 stat 调用获取所有文件元数据，减少系统调用次数
        try:
            stat_info = os.stat(log_file)
        except OSError:
            # 文件在扫描间隙被删除，本次跳过，等待下次发现新文件
            return events

        current_size  = stat_info.st_size
        current_inode = stat_info.st_ino   # Unix: inode; Windows NTFS: 文件索引号; FAT: 0
        current_mtime = stat_info.st_mtime
        basename = os.path.basename(log_file)

        stored = self._log_offsets.get(log_file)

        if stored is None:
            # 首次接触：仅读末尾，避免重复处理历史日志
            offset = max(0, current_size - _LOG_TAIL_SIZE)

        elif (current_inode != 0
              and stored.get("inode", 0) != 0
              and current_inode != stored.get("inode", 0)):
            # inode 不同 → 同路径下的文件已被替换（删除 + 重建）
            # 即使新文件比旧偏移量大，也必须从头读取，否则会漏报
            logger.debug(
                f"检测到日志文件被删除重建（inode变化），从头读取: {basename} "
                f"(旧inode={stored.get('inode', 0)}, 新inode={current_inode})"
            )
            offset = 0

        elif current_size < stored.get("offset", 0):
            # 文件大小 < 记录偏移 → 文件被截断或轮转（或 Windows FAT 下的兄底）
            logger.debug(
                f"检测到日志文件轮转/截断，从头读取: {basename} "
                f"(记录偏移={stored.get('offset', 0)}, 当前大小={current_size})"
            )
            offset = 0

        else:
            # 正常续读
            offset = stored.get("offset", 0)

        with open(log_file, "r", errors="ignore", encoding="utf-8") as f:
            f.seek(offset)
            new_content = f.read()
            new_offset = f.tell()

        # 更新内存偏移量记录（含 inode，供下次删除重建检测使用）
        self._log_offsets[log_file] = {
            "offset": new_offset,
            "size":   current_size,
            "mtime":  current_mtime,
            "inode":  current_inode,
        }

        if not new_content:
            return events

        parse_fn = WebLogParser.parse_apache if parser_type == "apache" else WebLogParser.parse_iis
        now = time.time()

        for line in new_content.splitlines():
            if not line.strip():
                continue
            parsed = parse_fn(line)
            if not parsed:
                continue
            line_events = self._analyze_request(parsed, now)
            events.extend(line_events)

        return events

    # ------------------------------------------------------------------
    # 内部：单请求多维度分析
    # ------------------------------------------------------------------

    def _analyze_request(self, req: dict, now: float) -> List[WebAttackEvent]:
        """
        对单条HTTP请求进行全类型攻击特征匹配。
        一条请求可能命中多种攻击类型，全部返回。
        """
        source_ip   = req.get("source_ip", "")
        method      = req.get("method", "GET")
        uri         = req.get("uri", "")
        referer     = req.get("referer", "")
        user_agent  = req.get("user_agent", "")
        status_code = req.get("status_code", 0)

        if not source_ip or not uri:
            return []

        # 多重解码防绕过
        decoded_uri = _multi_decode(uri)
        events: List[WebAttackEvent] = []

        # 1. SQL注入
        ev = self._match_patterns(decoded_uri, _SQL_PATTERNS, ATTACK_TYPE_SQL_INJECTION,
                                  source_ip, method, uri, referer, user_agent, now)
        if ev:
            events.append(ev)

        # 2. XSS攻击
        ev = self._match_patterns(decoded_uri, _XSS_PATTERNS, ATTACK_TYPE_XSS,
                                  source_ip, method, uri, referer, user_agent, now)
        if ev:
            events.append(ev)

        # 3. 目录遍历
        ev = self._match_patterns(decoded_uri, _DIR_TRAVERSAL_PATTERNS, ATTACK_TYPE_DIR_TRAVERSAL,
                                  source_ip, method, uri, referer, user_agent, now)
        if ev:
            events.append(ev)

        # 4. 命令注入
        ev = self._match_patterns(decoded_uri, _CMD_INJECTION_PATTERNS, ATTACK_TYPE_CMD_INJECTION,
                                  source_ip, method, uri, referer, user_agent, now)
        if ev:
            events.append(ev)

        # 5. CSRF（基于字段逻辑判断，含状态码过滤）
        ev = self._check_csrf(source_ip, method, uri, referer, user_agent, status_code, now)
        if ev:
            events.append(ev)

        # 6. 远程代码执行
        ev = self._match_patterns(decoded_uri, _RCE_PATTERNS, ATTACK_TYPE_RCE,
                                  source_ip, method, uri, referer, user_agent, now)
        if ev:
            events.append(ev)

        return events

    def _match_patterns(
        self,
        text: str,
        patterns: List[Tuple[re.Pattern, str]],
        attack_type: str,
        source_ip: str,
        method: str,
        uri: str,
        referer: str,
        user_agent: str,
        now: float,
    ) -> Optional[WebAttackEvent]:
        """遍历模式列表，匹配第一个命中的特征，受冷却期约束"""
        for pattern, desc in patterns:
            if pattern.search(text):
                if not self._check_cooldown(source_ip, attack_type, now):
                    return None
                return WebAttackEvent(
                    attack_type=attack_type,
                    source_ip=source_ip,
                    request_uri=uri[:500],
                    request_method=method,
                    matched_pattern=desc,
                    timestamp=now,
                    level=_ATTACK_LEVEL_MAP.get(attack_type, ATTACK_LEVEL_MEDIUM),
                    detection_method="log",
                    user_agent=user_agent[:200],
                    referer=referer[:200],
                )
        return None

    def _check_csrf(
        self, source_ip: str, method: str, uri: str,
        referer: str, user_agent: str, status_code: int, now: float,
    ) -> Optional[WebAttackEvent]:
        """
        CSRF嫌疑检测。

        判定条件（须同时满足）:
            1. 请求方法为状态变更方法（POST/PUT/DELETE/PATCH）
            2. 请求路径匹配敏感API路径模式（已排除 login/logout/register/auth）
            3. Referer字段为空或 "-"（无可追溯来源）
            4. HTTP状态码不是 4xx/5xx（服务端已拒绝的请求不可能造成CSRF危害）
            5. User-Agent 包含浏览器特征（CSRF 必须由受害者浏览器发起；
               API客户端/curl/脚本天然无 Referer，不属于 CSRF 场景）
        """
        if method not in _CSRF_STATE_CHANGING_METHODS:
            return None
        if not _CSRF_SENSITIVE_PATH_PATTERN.search(uri):
            return None
        if referer and referer.strip() not in ("", "-"):
            return None
        # 请求已被服务端拒绝（4xx/5xx），不会造成 CSRF 危害，跳过
        if status_code and 400 <= status_code < 600:
            return None
        # 非浏览器 User-Agent（curl/python-requests/okhttp 等 API 客户端）天然无
        # Referer，但这是合法行为，不属于 CSRF；CSRF 必须来自受害者浏览器
        ua = user_agent.strip()
        if not ua or not _BROWSER_UA_PATTERN.search(ua):
            return None
        if not self._check_cooldown(source_ip, ATTACK_TYPE_CSRF, now):
            return None
        return WebAttackEvent(
            attack_type=ATTACK_TYPE_CSRF,
            source_ip=source_ip,
            request_uri=uri[:500],
            request_method=method,
            matched_pattern="浏览器发起的敏感API状态变更请求缺少Referer头",
            timestamp=now,
            level=_ATTACK_LEVEL_MAP[ATTACK_TYPE_CSRF],
            detection_method="log",
            user_agent=user_agent[:200],
            referer="",
        )

    def _check_cooldown(self, source_ip: str, attack_type: str, now: float) -> bool:
        """
        检查冷却期。
        返回 True 表示冷却期已过（可以告警），同时更新时间戳；
        返回 False 表示仍在冷却期，不应重复告警。
        """
        key = f"{source_ip}:{attack_type}"
        with self._cooldown_lock:
            if now - self._cooldown_map.get(key, 0.0) < self._cooldown_seconds:
                return False
            self._cooldown_map[key] = now
        return True


# ---------------------------------------------------------------------------
# 主检测器：Web攻击检测（单例）
# ---------------------------------------------------------------------------

class WebAttackDetector:
    """
    Web攻击检测器（主类，单例）

    整合日志分析检测方法，统一管理生命周期，提供事件缓存和回调机制。

    日志源管理:
        - 启动时从 config_manager.get_web_log_sources() 加载配置
        - 每隔 _CONFIG_RELOAD_CYCLES 次轮询自动重新加载配置（约5分钟）
        - 也可通过 reload_log_sources() 立即热更新
        - 可通过 set_log_sources(sources) 直接设置，并同时持久化到 config_manager

    支持的攻击类型:
        - SQL注入       (sql_injection)
        - XSS攻击       (xss_attempt)
        - 目录遍历       (dir_traversal)
        - 命令注入       (cmd_injection)
        - CSRF          (csrf_attempt)
        - 远程代码执行   (rce_attempt)

    使用示例:
        # 配置日志源
        web_attack_detector.set_log_sources([
            {"path": "/var/log/nginx/access.log", "type": "nginx",  "enabled": True},
            {"path": "/opt/tomcat/logs",          "type": "tomcat", "enabled": True},
        ])
        # 启动检测
        web_attack_detector.start()
        # 取出事件
        events = web_attack_detector.get_recent_events()
        # 停止
        web_attack_detector.stop()
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if WebAttackDetector._initialized:
            return

        self._check_interval: float = float(
            DEFAULT_THRESHOLDS.get("web_attack_check_interval", 10)
        )
        self._cooldown_seconds: float = float(
            DEFAULT_THRESHOLDS.get("web_attack_cooldown", 60)
        )

        # 事件缓存（待上报）
        self._pending_events: List[WebAttackEvent] = []
        self._events_lock = threading.Lock()

        # 外部注册的回调列表
        self._callbacks: List[Callable[[WebAttackEvent], None]] = []

        # 日志分析检测器
        self._log_detector = LogBasedWebAttackDetector(
            cooldown_seconds=self._cooldown_seconds,
            on_detect=self._dispatch_event,
        )

        self._running = False
        self._stop_event = threading.Event()
        self._check_thread: Optional[threading.Thread] = None
        self._method_status: Dict[str, bool] = {"log": False}

        # 加载初始日志源配置
        self._load_sources_from_config()

        # 从持久化存储恢复日志读取偏移量，确保重启后不重复检测
        self._log_detector.load_offsets_from_config()

        WebAttackDetector._initialized = True

    # ------------------------------------------------------------------
    # 公开接口：日志源管理
    # ------------------------------------------------------------------

    def set_log_sources(self, sources: List[dict]):
        """
        设置Web日志源并立即生效，同时持久化到 config_manager。

        参数格式:
            [
                {"path": "/var/log/nginx/access.log", "type": "nginx",  "enabled": True},
                {"path": "/opt/tomcat/logs",          "type": "tomcat", "enabled": True},
                {"path": r"C:\\inetpub\\logs\\LogFiles", "type": "iis", "enabled": True},
            ]

        type 可选值: nginx | apache | iis | tomcat | auto
        """
        try:
            from config_manager import config_manager
            config_manager.set_web_log_sources(sources)
        except Exception as e:
            logger.warning(f"Web日志源配置持久化失败: {e}")

        self._log_detector.update_sources(sources)
        logger.info(
            f"Web日志源已更新: {[s.get('path', '') for s in sources if s.get('enabled', True)]}"
        )

    def reload_log_sources(self):
        """
        立即从 config_manager 重新加载日志源配置并生效。

        适用场景: 外部修改了配置文件后，需要立即使新配置生效而无需重启程序。
        """
        self._load_sources_from_config()

    # ------------------------------------------------------------------
    # 公开接口：生命周期
    # ------------------------------------------------------------------

    def add_event_callback(self, callback: Callable[[WebAttackEvent], None]):
        """注册事件回调函数，每次检测到攻击时触发"""
        self._callbacks.append(callback)

    def start(self) -> Dict[str, bool]:
        """
        启动Web攻击检测。

        返回各检测方法的启动状态字典，例如: {"log": True}
        """
        if self._running:
            return self._method_status.copy()

        self._running = True
        self._stop_event.clear()

        self._check_thread = threading.Thread(
            target=self._polling_loop,
            name="WebAttackCheckThread",
            daemon=True,
        )
        self._check_thread.start()
        self._method_status["log"] = True

        logger.info(
            f"Web攻击检测已启动 [日志分析] "
            f"(检测类型: SQL注入/XSS/目录遍历/命令注入/CSRF/RCE, "
            f"扫描间隔: {self._check_interval}秒, "
            f"配置热更新: 每{_CONFIG_RELOAD_CYCLES * int(self._check_interval)}秒)"
        )
        return self._method_status.copy()

    def stop(self):
        """停止所有检测线程，并持久化当前日志读取偏移量"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=5)

        # 正常停止时保存偏移量，下次启动从此处继续，避免重复处理
        self._log_detector.save_offsets_to_config()
        logger.info("Web攻击检测已停止，日志读取偏移量已保存")

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
        with self._log_detector._sources_lock:
            source_count = len(self._log_detector._configured_sources)
        return {
            "running":                self._running,
            "method_status":          self._method_status.copy(),
            "pending_events":         pending,
            "check_interval_seconds": self._check_interval,
            "cooldown_seconds":       self._cooldown_seconds,
            "configured_sources":     source_count,
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_sources_from_config(self):
        """从 config_manager 读取日志源配置并应用到检测器"""
        try:
            from config_manager import config_manager
            sources = config_manager.get_web_log_sources()
            self._log_detector.update_sources(sources)
            if sources:
                enabled = [s.get("path", "") for s in sources if s.get("enabled", True)]
                logger.info(f"已加载Web日志源配置: {enabled}")
            else:
                logger.info("未配置Web日志源，将自动发现系统日志文件")
        except Exception as e:
            logger.warning(f"读取Web日志源配置失败，使用自动发现模式: {e}")

    def _dispatch_event(self, event: WebAttackEvent):
        """
        内部事件分发：缓存事件 + 调用外部回调 + 记录告警日志。
        由各检测器在检测到攻击时调用，可能在不同线程中执行。
        """
        with self._events_lock:
            self._pending_events.append(event)
            # 防止无限增长
            if len(self._pending_events) > 2000:
                self._pending_events = self._pending_events[-2000:]

        logger.warning(
            f"[Web攻击告警] "
            f"类型={event.attack_type} "
            f"源IP={event.source_ip} "
            f"方法={event.request_method} "
            f"URI={event.request_uri[:100]} "
            f"特征={event.matched_pattern} "
            f"威胁等级={event.level}"
        )

        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Web攻击事件回调异常: {e}")

    def _polling_loop(self):
        """
        日志分析轮询主循环。
        每隔 _check_interval 秒执行一次，使用 Event.wait() 实现可中断等待。

        周期性任务（各自独立计数）:
            - 每 _OFFSET_SAVE_CYCLES  次（约60秒）: 持久化日志读取偏移量
            - 每 _CONFIG_RELOAD_CYCLES 次（约5分钟）: 重新加载日志源配置
            - 每 10 次（约100秒）: 清理过期冷却记录
        """
        cycle_counter  = 0
        offset_counter = 0
        cleanup_counter = 0

        while not self._stop_event.is_set():
            try:
                events = self._log_detector.check()
                for ev in events:
                    self._dispatch_event(ev)

                cycle_counter  += 1
                offset_counter += 1
                cleanup_counter += 1

                # 定期持久化日志读取偏移量（应对意外崩溃，限制重启后重复处理范围）
                if offset_counter >= _OFFSET_SAVE_CYCLES:
                    offset_counter = 0
                    self._log_detector.save_offsets_to_config()

                # 定期热更新日志源配置
                if cycle_counter >= _CONFIG_RELOAD_CYCLES:
                    cycle_counter = 0
                    self._load_sources_from_config()

                # 定期清理冷却期过期记录
                if cleanup_counter >= 10:
                    cleanup_counter = 0
                    self._log_detector.cleanup_stale()

            except Exception as e:
                logger.error(f"Web攻击检测轮询异常: {e}")

            self._stop_event.wait(self._check_interval)


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

web_attack_detector = WebAttackDetector()
