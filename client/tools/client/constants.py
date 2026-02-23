# -*- coding: utf-8 -*-
"""
模块名称: constants.py
模块功能: 从 client_config.json 的 settings 节加载所有可配置项，向各模块提供统一的常量访问接口

client_config.json 与本文件同目录，由服务端统一生成下发。
程序首次运行若文件不存在，则自动以内置默认值创建（标准 JSON，无注释）。

攻击类型标识符、授权状态值、响应码等内部固定字符串是代码逻辑标识，不受 JSON 控制，
始终在本文件末尾以 Python 常量方式定义。
"""

import os
import re
import json

# =============================================================================
# JSON 注释剥离（支持 JSONC 格式，即 // 行注释）
# =============================================================================

def _strip_comments(text: str) -> str:
    """
    从 JSONC 文本中移除 // 行注释，同时保留字符串内的 //（如 URL http://...）。
    使用正则优先匹配 JSON 字符串字面量，再匹配注释，注释部分替换为空字符串。
    """
    _pattern = re.compile(
        r'"(?:[^"\\]|\\.)*"'  # JSON 字符串（原样保留，其中的 // 不处理）
        r'|'
        r'//[^\n]*'           # // 行注释（移除）
    )
    return _pattern.sub(
        lambda m: m.group(0) if m.group(0).startswith('"') else '',
        text
    )


# =============================================================================
# 内置默认值（config 文件缺失或字段缺失时使用）
# =============================================================================

_DEFAULTS = {
    "server": {
        "url": "http://127.0.0.1:82/safe",
        "project_id": "2023031623403520002",
        "endpoints": {
            "register":         "/init/add",
            "heartbeat":        "/init/check",
            "attack_portscan":  "/init/attack/portscan",
            "attack_web":       "/init/attack/web",
            "rule_lib_version": "/attack/rule/version",
            "rule_lib_update":  "/attack/rule/update",
            "detector_status":  "/attack/detector/status",
            "attack_threshold": "/attack/threshold/get"
        }
    },
    "heartbeat": {
        "interval":       15,
        "request_timeout": 5,
        "max_retry":       5,
        "retry_interval":  1
    },
    "resources": {
        "cpu_peak_limit":            8,
        "cpu_avg_limit":             5,
        "cpu_throttle_threshold":    7,
        "cpu_throttle_sleep":        0.1,
        "cpu_sample_interval":       5,
        "memory_peak_limit":         300,
        "memory_resident_limit":     100,
        "memory_warning_threshold":  280,
        "disk_io_peak_limit":        10,
        "disk_io_avg_limit":          1,
        "disk_io_throttle_threshold": 9,
        "disk_io_throttle_sleep":    0.5
    },
    "logging": {
        "max_size":     10 * 1024 * 1024,
        "backup_count": 5,
        "buffer_size":  1024,
        "level":        "INFO",
        "file_prefix":  "client"
    },
    "auth": {
        "cache_ttl":            300,
        "offline_grace_period": 600
    },
    "storage": {
        "config_file_name":     "client_config.json",
        "config_dir_name":      "client_config",
        "config_dir_name_unix": ".client_config"
    },
    "crypto": {
        "aes_key_length": 128,
        "aes_block_size":  16
    },
    "hardware": {
        "cpu_usage_sample_interval": 0.5,
        "machine_id_file":           ".machine_id"
    },
    "attack_detection": {
        "rule_lib_sync_interval":        600,
        "rule_lib_file_path":            "data/rule_lib.json",
        "rule_lib_backup_path":          "data/rule_lib.backup.json",
        "attack_log_batch_size":         50,
        "attack_log_upload_interval":    30,
        "attack_detector_restart_delay":  3,
        "attack_detector_max_restart":   10,
        "traffic_queue_max_size":     10000,
        "traffic_collect_interval":     0.1,
        "traffic_baseline_samples":     100,
        "thresholds": {
            "ddos_syn_connections":              1000,
            "ddos_udp_pps":                     10000,
            "ddos_icmp_pps":                     5000,
            "ddos_traffic_mbps":                  100,
            "brute_force_fail_count":               5,
            "brute_force_time_window":             60,
            "port_scan_port_count":                20,
            "port_scan_time_window":               10,
            "web_attack_check_interval":           10,
            "web_attack_cooldown":                 60,
            "web_attack_log_tail_size":         65536,
            "traffic_burst_baseline_multiplier":   2.0,
            "traffic_baseline_window":            600
        }
    }
}

# 配置文件与本文件同目录
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_config.json")


def _deep_merge(base: dict, override: dict) -> dict:
    """将 override 的键递归合并到 base（override 优先），返回新字典"""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_settings() -> dict:
    """
    读取 client_config.json 中的 settings 节。
    - 文件存在：剥离注释后解析，将 settings 节与内置默认值深度合并（补全缺失字段）。
    - 文件不存在或损坏：写入包含默认值的完整模板文件，返回默认 settings。
    """
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = f.read()
            loaded = json.loads(_strip_comments(raw))
            if isinstance(loaded, dict):
                settings = loaded.get("settings", {})
                if isinstance(settings, dict):
                    return _deep_merge(_DEFAULTS, settings)
        except Exception:
            pass

    # 文件缺失或解析失败：生成完整默认模板（标准 JSON，无注释）
    _write_default_config()
    return _deep_merge({}, _DEFAULTS)


def _write_default_config() -> None:
    """将完整默认配置（settings + 空运行时状态）写入 client_config.json"""
    template = {
        "settings": _DEFAULTS,
        "client_id":           None,
        "machine_code":        None,
        "auth_key":            None,
        "expire_time":         None,
        "machine_name":        None,
        "ip_info":             None,
        "os_info":             None,
        "auth_cache":          None,
        "first_run_time":      None,
        "last_heartbeat_time": None,
        "web_log_offsets":     {},
        "web_log_sources":     []
    }
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# 加载 settings 节
_s = _load_settings()

# =============================================================================
# 服务端通信配置
# =============================================================================

_srv  = _s.get("server", {})
_ep   = _srv.get("endpoints", {})
_d_ep = _DEFAULTS["server"]["endpoints"]

SERVER_URL                      = _srv.get("url",             _DEFAULTS["server"]["url"])
PROJECT_ID                      = _srv.get("project_id",      _DEFAULTS["server"]["project_id"])
REGISTER_ENDPOINT               = _ep.get("register",         _d_ep["register"])
HEARTBEAT_ENDPOINT              = _ep.get("heartbeat",        _d_ep["heartbeat"])
ATTACK_LOG_UPLOAD_ENDPOINT      = _ep.get("attack_portscan",  _d_ep["attack_portscan"])
ATTACK_LOG_WEB_UPLOAD_ENDPOINT  = _ep.get("attack_web",       _d_ep["attack_web"])
RULE_LIB_VERSION_ENDPOINT       = _ep.get("rule_lib_version", _d_ep["rule_lib_version"])
RULE_LIB_UPDATE_ENDPOINT        = _ep.get("rule_lib_update",  _d_ep["rule_lib_update"])
ATTACK_DETECTOR_STATUS_ENDPOINT = _ep.get("detector_status",  _d_ep["detector_status"])
ATTACK_THRESHOLD_ENDPOINT       = _ep.get("attack_threshold", _d_ep["attack_threshold"])

# =============================================================================
# 心跳与重试配置
# =============================================================================

_hb   = _s.get("heartbeat", {})
_d_hb = _DEFAULTS["heartbeat"]

HEARTBEAT_INTERVAL = _hb.get("interval",        _d_hb["interval"])
REQUEST_TIMEOUT    = _hb.get("request_timeout",  _d_hb["request_timeout"])
MAX_RETRY          = _hb.get("max_retry",         _d_hb["max_retry"])
RETRY_INTERVAL     = _hb.get("retry_interval",    _d_hb["retry_interval"])

# =============================================================================
# 资源限制阈值
# =============================================================================

_res   = _s.get("resources", {})
_d_res = _DEFAULTS["resources"]

CPU_PEAK_LIMIT             = _res.get("cpu_peak_limit",            _d_res["cpu_peak_limit"])
CPU_AVG_LIMIT              = _res.get("cpu_avg_limit",             _d_res["cpu_avg_limit"])
CPU_THROTTLE_THRESHOLD     = _res.get("cpu_throttle_threshold",    _d_res["cpu_throttle_threshold"])
CPU_THROTTLE_SLEEP         = _res.get("cpu_throttle_sleep",        _d_res["cpu_throttle_sleep"])
CPU_SAMPLE_INTERVAL        = _res.get("cpu_sample_interval",       _d_res["cpu_sample_interval"])
MEMORY_PEAK_LIMIT          = _res.get("memory_peak_limit",         _d_res["memory_peak_limit"])
MEMORY_RESIDENT_LIMIT      = _res.get("memory_resident_limit",     _d_res["memory_resident_limit"])
MEMORY_WARNING_THRESHOLD   = _res.get("memory_warning_threshold",  _d_res["memory_warning_threshold"])
DISK_IO_PEAK_LIMIT         = _res.get("disk_io_peak_limit",        _d_res["disk_io_peak_limit"])
DISK_IO_AVG_LIMIT          = _res.get("disk_io_avg_limit",         _d_res["disk_io_avg_limit"])
DISK_IO_THROTTLE_THRESHOLD = _res.get("disk_io_throttle_threshold",_d_res["disk_io_throttle_threshold"])
DISK_IO_THROTTLE_SLEEP     = _res.get("disk_io_throttle_sleep",    _d_res["disk_io_throttle_sleep"])

# =============================================================================
# 日志配置
# =============================================================================

_log   = _s.get("logging", {})
_d_log = _DEFAULTS["logging"]

LOG_MAX_SIZE     = _log.get("max_size",     _d_log["max_size"])
LOG_BACKUP_COUNT = _log.get("backup_count", _d_log["backup_count"])
LOG_BUFFER_SIZE  = _log.get("buffer_size",  _d_log["buffer_size"])
LOG_LEVEL        = _log.get("level",        _d_log["level"])
LOG_FILE_PREFIX  = _log.get("file_prefix",  _d_log["file_prefix"])

# =============================================================================
# 授权相关配置
# =============================================================================

_auth   = _s.get("auth", {})
_d_auth = _DEFAULTS["auth"]

AUTH_CACHE_TTL       = _auth.get("cache_ttl",            _d_auth["cache_ttl"])
OFFLINE_GRACE_PERIOD = _auth.get("offline_grace_period", _d_auth["offline_grace_period"])

# =============================================================================
# 配置文件相关
# =============================================================================

_stor   = _s.get("storage", {})
_d_stor = _DEFAULTS["storage"]

CONFIG_FILE_NAME     = _stor.get("config_file_name",     _d_stor["config_file_name"])
CONFIG_DIR_NAME      = _stor.get("config_dir_name",      _d_stor["config_dir_name"])
CONFIG_DIR_NAME_UNIX = _stor.get("config_dir_name_unix", _d_stor["config_dir_name_unix"])

# =============================================================================
# AES 加密配置
# =============================================================================

_cry   = _s.get("crypto", {})
_d_cry = _DEFAULTS["crypto"]

AES_KEY_LENGTH = _cry.get("aes_key_length", _d_cry["aes_key_length"])
AES_BLOCK_SIZE = _cry.get("aes_block_size", _d_cry["aes_block_size"])

# =============================================================================
# 硬件采集配置
# =============================================================================

_hw   = _s.get("hardware", {})
_d_hw = _DEFAULTS["hardware"]

CPU_USAGE_SAMPLE_INTERVAL = _hw.get("cpu_usage_sample_interval", _d_hw["cpu_usage_sample_interval"])
MACHINE_ID_FILE           = _hw.get("machine_id_file",           _d_hw["machine_id_file"])

# =============================================================================
# 攻击检测配置
# =============================================================================

_atk   = _s.get("attack_detection", {})
_d_atk = _DEFAULTS["attack_detection"]

RULE_LIB_SYNC_INTERVAL        = _atk.get("rule_lib_sync_interval",        _d_atk["rule_lib_sync_interval"])
RULE_LIB_FILE_PATH             = _atk.get("rule_lib_file_path",             _d_atk["rule_lib_file_path"])
RULE_LIB_BACKUP_PATH           = _atk.get("rule_lib_backup_path",           _d_atk["rule_lib_backup_path"])
ATTACK_LOG_BATCH_SIZE          = _atk.get("attack_log_batch_size",          _d_atk["attack_log_batch_size"])
ATTACK_LOG_UPLOAD_INTERVAL     = _atk.get("attack_log_upload_interval",     _d_atk["attack_log_upload_interval"])
ATTACK_DETECTOR_RESTART_DELAY  = _atk.get("attack_detector_restart_delay",  _d_atk["attack_detector_restart_delay"])
ATTACK_DETECTOR_MAX_RESTART    = _atk.get("attack_detector_max_restart",    _d_atk["attack_detector_max_restart"])
TRAFFIC_QUEUE_MAX_SIZE         = _atk.get("traffic_queue_max_size",         _d_atk["traffic_queue_max_size"])
TRAFFIC_COLLECT_INTERVAL       = _atk.get("traffic_collect_interval",       _d_atk["traffic_collect_interval"])
TRAFFIC_BASELINE_SAMPLES       = _atk.get("traffic_baseline_samples",       _d_atk["traffic_baseline_samples"])
DEFAULT_THRESHOLDS             = dict(_atk.get("thresholds",                _d_atk["thresholds"]))

# =============================================================================
# 系统兼容性配置（固定，不写入 JSON）
# =============================================================================

MIN_PYTHON_VERSION = (3, 6)

SUPPORTED_OS = {
    "Windows": ["7", "8", "10", "11", "Server 2016", "Server 2019", "Server 2022"],
    "Linux": ["Ubuntu", "CentOS", "Debian", "Fedora", "openSUSE", "UOS", "Kylin", "Deepin"],
    "Darwin": ["10.14+"]
}

ATTACK_DETECTION_FALSE_POSITIVE_RATE = 0.03  # 误报率上限：3%
ATTACK_DETECTION_FALSE_NEGATIVE_RATE = 0.005  # 漏报率上限：0.5%

# =============================================================================
# 授权状态常量（代码内部固定标识符，不写入 JSON）
# =============================================================================

AUTH_STATUS_NORMAL  = "normal"   # 授权正常
AUTH_STATUS_EXPIRED = "expired"  # 授权已到期

RESPONSE_CODE_SUCCESS         = 0     # 请求成功
RESPONSE_CODE_AUTH_EXPIRED    = 1001  # 授权已到期
RESPONSE_CODE_INVALID_MACHINE = 1002  # 无效的机器码
RESPONSE_CODE_SERVER_ERROR    = 5000  # 服务端内部错误

# =============================================================================
# 攻击类型定义（代码内部固定标识符，不写入 JSON）
# =============================================================================

ATTACK_TYPE_DDOS_SYN      = "ddos_syn_flood"  # SYN Flood 攻击
ATTACK_TYPE_DDOS_UDP      = "ddos_udp_flood"  # UDP Flood 攻击
ATTACK_TYPE_DDOS_ICMP     = "ddos_icmp_flood" # ICMP Flood 攻击
ATTACK_TYPE_BRUTE_FORCE   = "brute_force"     # 暴力破解
ATTACK_TYPE_PORT_SCAN     = "port_scan"       # 端口扫描
ATTACK_TYPE_SQL_INJECTION = "sql_injection"   # SQL 注入
ATTACK_TYPE_XSS           = "xss_attempt"     # XSS 攻击
ATTACK_TYPE_DIR_TRAVERSAL = "dir_traversal"   # 目录遍历
ATTACK_TYPE_CMD_INJECTION = "cmd_injection"   # 命令注入
ATTACK_TYPE_CSRF          = "csrf_attempt"    # CSRF 攻击
ATTACK_TYPE_RCE           = "rce_attempt"     # 远程代码执行
ATTACK_TYPE_TRAFFIC_BURST = "traffic_burst"   # 异常流量突发
ATTACK_TYPE_MALWARE_C2    = "malware_c2"      # 恶意软件外联

ATTACK_LEVEL_HIGH   = "high"    # 高危
ATTACK_LEVEL_MEDIUM = "medium"  # 中危
ATTACK_LEVEL_LOW    = "low"     # 低危
