# -*- coding: utf-8 -*-
"""
模块名称: constants.py
模块功能: 定义客户端程序的所有常量和可配置项
依赖模块: 无（纯Python标准库）
系统适配: 所有平台通用

说明:
    本模块集中管理所有配置项，支持外部修改无需改动代码。
    配置项分为以下几类：
    1. 服务端通信配置
    2. 心跳与重试配置
    3. 资源限制阈值
    4. 日志配置
    5. 授权相关配置
"""

# =============================================================================
# 服务端通信配置
# =============================================================================

# 服务端API基础地址，用户可根据实际部署情况修改
SERVER_URL = "http://127.0.0.1:82/safe"  # 服务端API地址，格式: http(s)://host:port/path

# 注册接口路径，客户端首次运行时调用
REGISTER_ENDPOINT = "/init/add"  # 注册接口，用于首次注册或更新机器信息

# 心跳接口路径，客户端定时调用
HEARTBEAT_ENDPOINT = "/init/check"  # 心跳接口，用于定时上报状态并获取授权状态

# =============================================================================
# 心跳与重试配置
# =============================================================================

# 心跳间隔时间（秒），严格控制为15秒
HEARTBEAT_INTERVAL = 15  # 心跳发送间隔，单位：秒

# HTTP请求超时时间（秒），避免网络阻塞导致程序卡死
REQUEST_TIMEOUT = 5  # 网络请求超时时间，单位：秒，不超过3秒

# 请求失败后的最大重试次数
MAX_RETRY = 5  # 网络请求失败后的重试次数上限

# 重试间隔时间（秒）
RETRY_INTERVAL = 1  # 每次重试之间的等待时间，单位：秒

# =============================================================================
# 资源限制阈值（严格约束）
# =============================================================================

# CPU占用限制
CPU_PEAK_LIMIT = 8  # CPU峰值上限，单位：%，超过此值需要降速
CPU_AVG_LIMIT = 5  # CPU平均值上限，单位：%
CPU_THROTTLE_THRESHOLD = 7  # CPU节流阈值，超过此值主动休眠
CPU_THROTTLE_SLEEP = 0.1  # CPU超限时的休眠时间，单位：秒
CPU_SAMPLE_INTERVAL = 5  # CPU采样间隔，单位：秒

# 内存占用限制
MEMORY_PEAK_LIMIT = 300  # 内存峰值上限，单位：MB
MEMORY_RESIDENT_LIMIT = 100  # 常驻内存上限，单位：MB
MEMORY_WARNING_THRESHOLD = 280  # 内存警告阈值，超过此值释放缓存，单位：MB

# 磁盘IO限制
DISK_IO_PEAK_LIMIT = 10  # 磁盘IO峰值上限，单位：MB/s
DISK_IO_AVG_LIMIT = 1  # 磁盘IO平均上限，单位：MB/s
DISK_IO_THROTTLE_THRESHOLD = 9  # 磁盘IO节流阈值，单位：MB/s
DISK_IO_THROTTLE_SLEEP = 0.5  # 磁盘IO超限时的暂停时间，单位：秒

# =============================================================================
# 日志配置
# =============================================================================

# 单个日志文件的最大大小（字节），超过后自动切割
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB，日志文件大小上限

# 日志文件备份数量
LOG_BACKUP_COUNT = 5  # 保留最近5个日志备份文件

# 日志写入缓冲区大小（字节）
LOG_BUFFER_SIZE = 1024  # 1KB，批量写入缓冲区大小

# 日志级别
LOG_LEVEL = "INFO"  # 默认日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL

# 日志文件名前缀
LOG_FILE_PREFIX = "client"  # 日志文件名前缀，生成格式：client.log

# =============================================================================
# 授权相关配置
# =============================================================================

# 授权状态缓存有效期（秒）
AUTH_CACHE_TTL = 300  # 5分钟，授权状态本地缓存有效期

# 离线宽限期（秒），网络不可用时允许临时运行的最长时间
OFFLINE_GRACE_PERIOD = 600  # 10分钟，离线状态下允许运行的最长时间

# =============================================================================
# 配置文件相关
# =============================================================================

# 配置文件名
CONFIG_FILE_NAME = "client_config.json"  # 配置文件名称

# 配置文件目录名（用于各平台）
CONFIG_DIR_NAME = "client_config"  # Windows: %APPDATA%/client_config
CONFIG_DIR_NAME_UNIX = ".client_config"  # Linux/macOS: ~/.client_config

# =============================================================================
# AES加密配置
# =============================================================================

# AES密钥长度（位）
AES_KEY_LENGTH = 128  # 128位AES密钥，即16字节

# AES块大小（字节）
AES_BLOCK_SIZE = 16  # AES块大小固定为16字节

# =============================================================================
# 硬件采集配置
# =============================================================================

# CPU使用率采样间隔（秒），降低CPU占用
CPU_USAGE_SAMPLE_INTERVAL = 0.5  # CPU使用率采样间隔，不超过0.5秒

# 机器码持久化文件名（UUID兜底时使用）
MACHINE_ID_FILE = ".machine_id"  # 机器码持久化文件名

# =============================================================================
# 系统兼容性配置
# =============================================================================

# 支持的最低Python版本
MIN_PYTHON_VERSION = (3, 6)  # 最低Python 3.6

# 支持的操作系统列表（用于检测和提示）
SUPPORTED_OS = {
    "Windows": ["7", "8", "10", "11", "Server 2016", "Server 2019", "Server 2022"],
    "Linux": ["Ubuntu", "CentOS", "Debian", "Fedora", "openSUSE", "UOS", "Kylin", "Deepin"],
    "Darwin": ["10.14+"]  # macOS Mojave及以上
}

# =============================================================================
# 授权状态常量
# =============================================================================

# 授权状态枚举值
AUTH_STATUS_NORMAL = "normal"  # 授权正常
AUTH_STATUS_EXPIRED = "expired"  # 授权已到期

# API响应码
RESPONSE_CODE_SUCCESS = 0  # 请求成功
RESPONSE_CODE_AUTH_EXPIRED = 1001  # 授权已到期
RESPONSE_CODE_INVALID_MACHINE = 1002  # 无效的机器码
RESPONSE_CODE_SERVER_ERROR = 5000  # 服务端内部错误

PROJECT_ID="2023031623403520002"

# =============================================================================
# 攻击识别与特征库管理配置
# =============================================================================

# 特征库同步配置
RULE_LIB_SYNC_INTERVAL = 600  # 特征库主动拉取间隔，单位：秒（10分钟）
RULE_LIB_VERSION_ENDPOINT = "/attack/rule/version"  # 特征库版本查询接口
RULE_LIB_UPDATE_ENDPOINT = "/attack/rule/update"  # 特征库增量更新接口
RULE_LIB_FILE_PATH = "data/rule_lib.json"  # 特征库本地存储路径
RULE_LIB_BACKUP_PATH = "data/rule_lib.backup.json"  # 特征库备份路径

# 攻击日志上传配置
ATTACK_LOG_UPLOAD_ENDPOINT = "/init/attack/portscan"  # 端口扫描日志上传接口
ATTACK_LOG_WEB_UPLOAD_ENDPOINT = "/init/attack/web"  # Web攻击日志上传接口
ATTACK_LOG_BATCH_SIZE = 50  # 批量上传日志数量
ATTACK_LOG_UPLOAD_INTERVAL = 30  # 日志上传间隔，单位：秒

# 攻击识别异常上报配置
ATTACK_DETECTOR_STATUS_ENDPOINT = "/attack/detector/status"  # 识别模块状态上报接口
ATTACK_DETECTOR_RESTART_DELAY = 3  # 模块异常后重启延迟，单位：秒
ATTACK_DETECTOR_MAX_RESTART = 10  # 最大重启次数

# 阈值配置下发接口
ATTACK_THRESHOLD_ENDPOINT = "/attack/threshold/get"  # 阈值配置获取接口

# 攻击类型定义
ATTACK_TYPE_DDOS_SYN = "ddos_syn_flood"  # SYN Flood攻击
ATTACK_TYPE_DDOS_UDP = "ddos_udp_flood"  # UDP Flood攻击
ATTACK_TYPE_DDOS_ICMP = "ddos_icmp_flood"  # ICMP Flood攻击
ATTACK_TYPE_BRUTE_FORCE = "brute_force"  # 暴力破解
ATTACK_TYPE_PORT_SCAN = "port_scan"  # 端口扫描
ATTACK_TYPE_SQL_INJECTION = "sql_injection"  # SQL注入
ATTACK_TYPE_XSS = "xss_attempt"  # XSS攻击
ATTACK_TYPE_DIR_TRAVERSAL = "dir_traversal"  # 目录遍历攻击
ATTACK_TYPE_CMD_INJECTION = "cmd_injection"  # 命令注入攻击
ATTACK_TYPE_CSRF = "csrf_attempt"  # CSRF攻击
ATTACK_TYPE_RCE = "rce_attempt"  # 远程代码执行攻击
ATTACK_TYPE_TRAFFIC_BURST = "traffic_burst"  # 异常流量突发
ATTACK_TYPE_MALWARE_C2 = "malware_c2"  # 恶意软件外联

# 攻击等级定义
ATTACK_LEVEL_HIGH = "high"  # 高危
ATTACK_LEVEL_MEDIUM = "medium"  # 中危
ATTACK_LEVEL_LOW = "low"  # 低危

# 攻击识别默认阈值
DEFAULT_THRESHOLDS = {
    # DDoS攻击阈值
    "ddos_syn_connections": 1000,  # SYN连接数阈值
    "ddos_udp_pps": 10000,  # UDP包速率阈值（包/秒）
    "ddos_icmp_pps": 5000,  # ICMP包速率阈值（包/秒）
    "ddos_traffic_mbps": 100,  # 流量峰值阈值（MB/s）

    # 暴力破解阈值
    "brute_force_fail_count": 5,  # 失败次数阈值
    "brute_force_time_window": 60,  # 时间窗口（秒）

    # 端口扫描阈值
    "port_scan_port_count": 20,  # 扫描端口数量阈值
    "port_scan_time_window": 10,  # 时间窗口（秒）

    # Web攻击检测阈值
    "web_attack_check_interval": 10,  # Web日志扫描间隔（秒）
    "web_attack_cooldown": 60,  # 同一IP同类攻击告警冷却时间（秒）
    "web_attack_log_tail_size": 65536,  # 首次读取日志末尾大小（字节，64KB）

    # 异常流量突发阈值
    "traffic_burst_baseline_multiplier": 2.0,  # 基线倍数（200%）
    "traffic_baseline_window": 600,  # 基线统计窗口（秒，10分钟）
}

# 流量采集配置
TRAFFIC_QUEUE_MAX_SIZE = 10000  # 流量数据队列最大长度
TRAFFIC_COLLECT_INTERVAL = 0.1  # 流量采集间隔，单位：秒
TRAFFIC_BASELINE_SAMPLES = 100  # 基线统计样本数量

# 性能要求
ATTACK_DETECTION_FALSE_POSITIVE_RATE = 0.03  # 误报率上限：3%
ATTACK_DETECTION_FALSE_NEGATIVE_RATE = 0.005  # 漏报率上限：0.5%
