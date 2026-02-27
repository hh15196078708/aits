package vip.xiaonuo.ewm.modular.project.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 客户端配置文件实体（对应 client_config.json 完整结构）
 * <p>
 * 该配置由服务端统一生成下发至客户端，包含两大部分：
 * 1. 运行时状态字段 — 由客户端程序运行时动态更新
 * 2. settings 配置节 — 控制各模块的行为参数
 *
 * @author Richai
 * @date 2026/02/25
 */
@Data
@Schema(description = "客户端配置文件实体")
public class EwmClientConfig {

    // =========================================================================
    // 运行时状态字段
    // =========================================================================

    /** 服务端分配的客户端唯一标识 */
    @JsonProperty("client_id")
    @Schema(description = "服务端分配的客户端唯一标识")
    private String clientId;

    /** 机器唯一码，由硬件信息生成 */
    @JsonProperty("machine_code")
    @Schema(description = "机器唯一码")
    private String machineCode;

    /** 授权密钥（MD5格式），注册时由服务端下发 */
    @JsonProperty("auth_key")
    @Schema(description = "授权密钥")
    private String authKey;

    /** 授权到期时间，过期后客户端拒绝运行 */
    @JsonProperty("expire_time")
    @Schema(description = "授权到期时间")
    private String expireTime;

    /** 机器主机名 */
    @JsonProperty("machine_name")
    @Schema(description = "机器主机名")
    private String machineName;

    /** 首次运行的Unix时间戳，仅首次注册时写入 */
    @JsonProperty("first_run_time")
    @Schema(description = "首次运行时间戳（Unix秒）")
    private Long firstRunTime;

    /** 最后一次心跳成功的Unix时间戳 */
    @JsonProperty("last_heartbeat_time")
    @Schema(description = "最后心跳时间戳（Unix秒）")
    private Long lastHeartbeatTime;

    /** 已封禁的IP列表 */
    @JsonProperty("blocked_ips")
    @Schema(description = "已封禁的IP列表")
    private List<String> blockedIps = new ArrayList<>();

    /** 本机IP信息 */
    @JsonProperty("ip_info")
    @Schema(description = "本机IP信息")
    private IpInfo ipInfo;

    /** 操作系统信息 */
    @JsonProperty("os_info")
    @Schema(description = "操作系统信息")
    private OsInfo osInfo;

    /** 授权状态缓存 */
    @JsonProperty("auth_cache")
    @Schema(description = "授权状态缓存")
    private AuthCache authCache;

    /** Web日志文件增量读取偏移量 */
    @JsonProperty("web_log_offsets")
    @Schema(description = "Web日志文件读取偏移量")
    private Map<String, Object> webLogOffsets = new HashMap<>();

    /** Web日志源配置列表 */
    @JsonProperty("web_log_sources")
    @Schema(description = "Web日志源配置列表")
    private List<WebLogSource> webLogSources = new ArrayList<>();

    /** 全部设置项 */
    @Schema(description = "设置项")
    private Settings settings = new Settings();

    // =========================================================================
    // IP信息
    // =========================================================================

    @Data
    @Schema(description = "IP信息")
    public static class IpInfo {

        /** 内网IP */
        @JsonProperty("internal_ip")
        @Schema(description = "内网IP")
        private String internalIp;

        /** 外网IP */
        @JsonProperty("external_ip")
        @Schema(description = "外网IP")
        private String externalIp;

        /** IP获取方式 */
        @Schema(description = "IP获取方式（psutil/socket等）")
        private String source;
    }

    // =========================================================================
    // 操作系统信息
    // =========================================================================

    @Data
    @Schema(description = "操作系统信息")
    public static class OsInfo {

        /** 系统类型（Windows/Linux/Darwin） */
        @Schema(description = "系统类型")
        private String type;

        /** 系统版本号 */
        @Schema(description = "系统版本号")
        private String version;

        /** 系统架构（64bit/32bit） */
        @Schema(description = "系统架构")
        private String arch;

        /** 内核版本 */
        @Schema(description = "内核版本")
        private String kernel;

        /** 主机名 */
        @Schema(description = "主机名")
        private String hostname;
    }

    // =========================================================================
    // 授权状态缓存
    // =========================================================================

    @Data
    @Schema(description = "授权状态缓存")
    public static class AuthCache {

        /** 授权状态（normal-正常，expired-到期） */
        @Schema(description = "授权状态（normal/expired）")
        private String status = "normal";

        /** 缓存更新的Unix时间戳 */
        @JsonProperty("update_time")
        @Schema(description = "缓存更新时间戳（Unix秒）")
        private Long updateTime;
    }

    // =========================================================================
    // Web日志源配置
    // =========================================================================

    @Data
    @Schema(description = "Web日志源配置")
    public static class WebLogSource {

        /** 日志文件或目录路径 */
        @Schema(description = "日志文件或目录路径")
        private String path;

        /** 日志格式类型（nginx/apache/iis/tomcat/auto） */
        @Schema(description = "日志格式类型（nginx/apache/iis/tomcat/auto）")
        private String type;

        /** 是否启用该日志源 */
        @Schema(description = "是否启用")
        private Boolean enabled = true;
    }

    // =========================================================================
    // Settings 配置节
    // =========================================================================

    @Data
    @Schema(description = "客户端设置项")
    public static class Settings {

        /** 服务端通信配置 */
        @Schema(description = "服务端通信配置")
        private Server server = new Server();

        /** WebSocket配置 */
        @Schema(description = "WebSocket配置")
        private Websocket websocket = new Websocket();

        /** 心跳配置 */
        @Schema(description = "心跳配置")
        private Heartbeat heartbeat = new Heartbeat();

        /** 授权管理配置 */
        @Schema(description = "授权管理配置")
        private Auth auth = new Auth();

        /** 资源限制配置 */
        @Schema(description = "资源限制配置")
        private Resources resources = new Resources();

        /** 日志配置 */
        @Schema(description = "日志配置")
        private Logging logging = new Logging();

        /** AES加密配置 */
        @Schema(description = "AES加密配置")
        private Crypto crypto = new Crypto();

        /** 硬件采集配置 */
        @Schema(description = "硬件采集配置")
        private Hardware hardware = new Hardware();

        /** 存储配置 */
        @Schema(description = "存储配置")
        private Storage storage = new Storage();

        /** 攻击检测配置 */
        @JsonProperty("attack_detection")
        @Schema(description = "攻击检测配置")
        private AttackDetection attackDetection = new AttackDetection();

        /** Payload嗅探配置 */
        @JsonProperty("payload_sniffer")
        @Schema(description = "Payload嗅探配置")
        private PayloadSniffer payloadSniffer = new PayloadSniffer();

        /** 进程监控配置 */
        @JsonProperty("process_monitor")
        @Schema(description = "进程监控配置")
        private ProcessMonitor processMonitor = new ProcessMonitor();

        /** IP拉黑配置 */
        @JsonProperty("ip_blocker")
        @Schema(description = "IP拉黑配置")
        private IpBlocker ipBlocker = new IpBlocker();
    }

    // =========================================================================
    // settings.server — 服务端通信配置
    // =========================================================================

    @Data
    @Schema(description = "服务端通信配置")
    public static class Server {

        /** 服务端API基础地址 */
        @Schema(description = "服务端API基础地址")
        private String url = "http://127.0.0.1:82/safe";

        /** 项目ID */
        @JsonProperty("project_id")
        @Schema(description = "项目ID")
        private String projectId = "2023031623403520002";

        /** 接口路径配置 */
        @Schema(description = "接口路径配置")
        private Endpoints endpoints = new Endpoints();
    }

    @Data
    @Schema(description = "接口路径配置")
    public static class Endpoints {

        /** 注册/更新接口 */
        @Schema(description = "注册/更新接口路径")
        private String register = "/init/add";

        /** 心跳接口 */
        @Schema(description = "心跳接口路径")
        private String heartbeat = "/init/check";

        /** Web攻击日志统一上报接口 */
        @JsonProperty("attack_unified")
        @Schema(description = "统一攻击日志上报接口路径")
        private String attackUnified = "/init/attack/web";

        /** IP白名单获取接口 */
        @JsonProperty("ip_whitelist")
        @Schema(description = "IP白名单获取接口路径")
        private String ipWhitelist = "/init/whitelist/get";

        /** 端口扫描攻击日志上报接口 */
        @JsonProperty("attack_portscan")
        @Schema(description = "端口扫描攻击日志上报接口路径")
        private String attackPortscan = "/init/attack/portscan";

        /** 流量攻击日志上报接口 */
        @JsonProperty("attack_traffic")
        @Schema(description = "流量攻击日志上报接口路径")
        private String attackTraffic = "/init/attack/traffic";

        /** Web攻击日志上报接口 */
        @JsonProperty("attack_web")
        @Schema(description = "Web攻击日志上报接口路径")
        private String attackWeb = "/init/attack/web";

        /** 攻击阈值获取接口 */
        @JsonProperty("attack_threshold")
        @Schema(description = "攻击阈值获取接口路径")
        private String attackThreshold = "/attack/threshold/get";

        /** 检测器状态上报接口 */
        @JsonProperty("detector_status")
        @Schema(description = "检测器状态上报接口路径")
        private String detectorStatus = "/attack/detector/status";

        /** 规则库版本查询接口 */
        @JsonProperty("rule_lib_version")
        @Schema(description = "规则库版本查询接口路径")
        private String ruleLibVersion = "/attack/rule/version";

        /** 规则库更新下载接口 */
        @JsonProperty("rule_lib_update")
        @Schema(description = "规则库更新下载接口路径")
        private String ruleLibUpdate = "/attack/rule/update";
    }

    // =========================================================================
    // settings.websocket — WebSocket配置
    // =========================================================================

    @Data
    @Schema(description = "WebSocket配置")
    public static class Websocket {

        /** WSS基础地址，连接时末尾自动拼接 /{clientId} */
        @Schema(description = "WSS基础地址")
        private String url = "ws://127.0.0.1:82/safe/init/ws";

        /** 断线重连间隔（秒） */
        @JsonProperty("reconnect_interval")
        @Schema(description = "断线重连间隔（秒）")
        private Integer reconnectInterval = 5;

        /** SSL证书验证（自签名证书可设为false） */
        @JsonProperty("ssl_verify")
        @Schema(description = "是否验证SSL证书")
        private Boolean sslVerify = true;
    }

    // =========================================================================
    // settings.heartbeat — 心跳配置
    // =========================================================================

    @Data
    @Schema(description = "心跳配置")
    public static class Heartbeat {

        /** 心跳发送间隔（秒） */
        @Schema(description = "心跳发送间隔（秒）")
        private Integer interval = 15;

        /** 单次HTTP请求超时时间（秒） */
        @JsonProperty("request_timeout")
        @Schema(description = "请求超时时间（秒）")
        private Integer requestTimeout = 5;

        /** 请求失败最大重试次数 */
        @JsonProperty("max_retry")
        @Schema(description = "最大重试次数")
        private Integer maxRetry = 5;

        /** 重试间隔（秒） */
        @JsonProperty("retry_interval")
        @Schema(description = "重试间隔（秒）")
        private Integer retryInterval = 1;
    }

    // =========================================================================
    // settings.auth — 授权管理配置
    // =========================================================================

    @Data
    @Schema(description = "授权管理配置")
    public static class Auth {

        /** 授权状态缓存有效期（秒），有效期内不重复验证 */
        @JsonProperty("cache_ttl")
        @Schema(description = "授权缓存有效期（秒）")
        private Integer cacheTtl = 300;

        /** 离线宽限期（秒），网络断开后允许继续运行的最长时间 */
        @JsonProperty("offline_grace_period")
        @Schema(description = "离线宽限期（秒）")
        private Integer offlineGracePeriod = 600;
    }

    // =========================================================================
    // settings.resources — 资源限制配置
    // =========================================================================

    @Data
    @Schema(description = "资源限制配置")
    public static class Resources {

        /** CPU峰值使用率上限（%） */
        @JsonProperty("cpu_peak_limit")
        @Schema(description = "CPU峰值上限（%）")
        private Integer cpuPeakLimit = 8;

        /** CPU平均使用率上限（%） */
        @JsonProperty("cpu_avg_limit")
        @Schema(description = "CPU平均上限（%）")
        private Integer cpuAvgLimit = 5;

        /** CPU节流触发阈值（%），超过时休眠节流 */
        @JsonProperty("cpu_throttle_threshold")
        @Schema(description = "CPU节流阈值（%）")
        private Integer cpuThrottleThreshold = 7;

        /** CPU节流休眠时间（秒） */
        @JsonProperty("cpu_throttle_sleep")
        @Schema(description = "CPU节流休眠时间（秒）")
        private Double cpuThrottleSleep = 0.1;

        /** CPU采样间隔（秒） */
        @JsonProperty("cpu_sample_interval")
        @Schema(description = "CPU采样间隔（秒）")
        private Integer cpuSampleInterval = 5;

        /** 内存峰值上限（MB） */
        @JsonProperty("memory_peak_limit")
        @Schema(description = "内存峰值上限（MB）")
        private Integer memoryPeakLimit = 300;

        /** 内存常驻上限（MB） */
        @JsonProperty("memory_resident_limit")
        @Schema(description = "内存常驻上限（MB）")
        private Integer memoryResidentLimit = 100;

        /** 内存告警阈值（MB），超过时触发GC */
        @JsonProperty("memory_warning_threshold")
        @Schema(description = "内存告警阈值（MB）")
        private Integer memoryWarningThreshold = 280;

        /** 磁盘IO峰值上限（MB/s） */
        @JsonProperty("disk_io_peak_limit")
        @Schema(description = "磁盘IO峰值上限（MB/s）")
        private Integer diskIoPeakLimit = 10;

        /** 磁盘IO平均上限（MB/s） */
        @JsonProperty("disk_io_avg_limit")
        @Schema(description = "磁盘IO平均上限（MB/s）")
        private Integer diskIoAvgLimit = 1;

        /** 磁盘IO节流触发阈值（MB/s） */
        @JsonProperty("disk_io_throttle_threshold")
        @Schema(description = "磁盘IO节流阈值（MB/s）")
        private Integer diskIoThrottleThreshold = 9;

        /** 磁盘IO节流休眠时间（秒） */
        @JsonProperty("disk_io_throttle_sleep")
        @Schema(description = "磁盘IO节流休眠时间（秒）")
        private Double diskIoThrottleSleep = 0.5;
    }

    // =========================================================================
    // settings.logging — 日志配置
    // =========================================================================

    @Data
    @Schema(description = "日志配置")
    public static class Logging {

        /** 日志级别（DEBUG/INFO/WARNING/ERROR） */
        @Schema(description = "日志级别")
        private String level = "INFO";

        /** 单个日志文件最大大小（字节），默认10MB */
        @JsonProperty("max_size")
        @Schema(description = "单个日志文件最大大小（字节）")
        private Integer maxSize = 10485760;

        /** 日志轮转备份数量 */
        @JsonProperty("backup_count")
        @Schema(description = "日志备份数量")
        private Integer backupCount = 5;

        /** 日志缓冲区大小（字节） */
        @JsonProperty("buffer_size")
        @Schema(description = "日志缓冲区大小（字节）")
        private Integer bufferSize = 1024;

        /** 日志文件名前缀 */
        @JsonProperty("file_prefix")
        @Schema(description = "日志文件名前缀")
        private String filePrefix = "client";
    }

    // =========================================================================
    // settings.crypto — AES加密配置
    // =========================================================================

    @Data
    @Schema(description = "AES加密配置")
    public static class Crypto {

        /** AES密钥长度（位） */
        @JsonProperty("aes_key_length")
        @Schema(description = "AES密钥长度（位）")
        private Integer aesKeyLength = 128;

        /** AES分组大小（字节） */
        @JsonProperty("aes_block_size")
        @Schema(description = "AES分组大小（字节）")
        private Integer aesBlockSize = 16;
    }

    // =========================================================================
    // settings.hardware — 硬件采集配置
    // =========================================================================

    @Data
    @Schema(description = "硬件采集配置")
    public static class Hardware {

        /** CPU使用率采样间隔（秒） */
        @JsonProperty("cpu_usage_sample_interval")
        @Schema(description = "CPU使用率采样间隔（秒）")
        private Double cpuUsageSampleInterval = 0.5;

        /** 机器ID持久化文件名 */
        @JsonProperty("machine_id_file")
        @Schema(description = "机器ID持久化文件名")
        private String machineIdFile = ".machine_id";
    }

    // =========================================================================
    // settings.storage — 存储配置
    // =========================================================================

    @Data
    @Schema(description = "存储配置")
    public static class Storage {

        /** 配置文件名称 */
        @JsonProperty("config_file_name")
        @Schema(description = "配置文件名称")
        private String configFileName = "client_config.json";

        /** Windows下配置目录名称 */
        @JsonProperty("config_dir_name")
        @Schema(description = "Windows下配置目录名称")
        private String configDirName = "client_config";

        /** Unix下配置目录名称（点号开头隐藏） */
        @JsonProperty("config_dir_name_unix")
        @Schema(description = "Unix下配置目录名称")
        private String configDirNameUnix = ".client_config";
    }

    // =========================================================================
    // settings.attack_detection — 攻击检测配置
    // =========================================================================

    @Data
    @Schema(description = "攻击检测配置")
    public static class AttackDetection {

        /** 攻击日志批量上报大小 */
        @JsonProperty("attack_log_batch_size")
        @Schema(description = "攻击日志批量上报大小")
        private Integer attackLogBatchSize = 50;

        /** 攻击日志上报间隔（秒） */
        @JsonProperty("attack_log_upload_interval")
        @Schema(description = "攻击日志上报间隔（秒）")
        private Integer attackLogUploadInterval = 30;

        /** 攻击检测器最大重启次数 */
        @JsonProperty("attack_detector_max_restart")
        @Schema(description = "攻击检测器最大重启次数")
        private Integer attackDetectorMaxRestart = 10;

        /** 攻击检测器重启延迟（秒） */
        @JsonProperty("attack_detector_restart_delay")
        @Schema(description = "攻击检测器重启延迟（秒）")
        private Integer attackDetectorRestartDelay = 3;

        /** 规则库文件路径 */
        @JsonProperty("rule_lib_file_path")
        @Schema(description = "规则库文件路径")
        private String ruleLibFilePath = "data/rule_lib.json";

        /** 规则库备份文件路径 */
        @JsonProperty("rule_lib_backup_path")
        @Schema(description = "规则库备份文件路径")
        private String ruleLibBackupPath = "data/rule_lib.backup.json";

        /** 规则库同步间隔（秒） */
        @JsonProperty("rule_lib_sync_interval")
        @Schema(description = "规则库同步间隔（秒）")
        private Integer ruleLibSyncInterval = 600;

        /** 流量基线采样数量 */
        @JsonProperty("traffic_baseline_samples")
        @Schema(description = "流量基线采样数量")
        private Integer trafficBaselineSamples = 100;

        /** 流量采集间隔（秒） */
        @JsonProperty("traffic_collect_interval")
        @Schema(description = "流量采集间隔（秒）")
        private Double trafficCollectInterval = 0.1;

        /** 流量队列最大大小 */
        @JsonProperty("traffic_queue_max_size")
        @Schema(description = "流量队列最大大小")
        private Integer trafficQueueMaxSize = 10000;

        /** 攻击检测阈值配置 */
        @Schema(description = "攻击检测阈值配置")
        private Thresholds thresholds = new Thresholds();
    }

    @Data
    @Schema(description = "攻击检测阈值配置")
    public static class Thresholds {

        /** 端口扫描判定阈值：同一IP在时间窗口内扫描的端口数 */
        @JsonProperty("port_scan_port_count")
        @Schema(description = "端口扫描端口数阈值")
        private Integer portScanPortCount = 20;

        /** 端口扫描时间窗口（秒） */
        @JsonProperty("port_scan_time_window")
        @Schema(description = "端口扫描时间窗口（秒）")
        private Integer portScanTimeWindow = 10;

        /** 暴力破解判定阈值：同一IP在时间窗口内的失败次数 */
        @JsonProperty("brute_force_fail_count")
        @Schema(description = "暴力破解失败次数阈值")
        private Integer bruteForceFailCount = 5;

        /** 暴力破解时间窗口（秒） */
        @JsonProperty("brute_force_time_window")
        @Schema(description = "暴力破解时间窗口（秒）")
        private Integer bruteForceTimeWindow = 60;

        /** DDoS SYN Flood判定阈值（并发连接数） */
        @JsonProperty("ddos_syn_connections")
        @Schema(description = "SYN Flood并发连接数阈值")
        private Integer ddosSynConnections = 1000;

        /** DDoS UDP Flood判定阈值（每秒包数） */
        @JsonProperty("ddos_udp_pps")
        @Schema(description = "UDP Flood每秒包数阈值")
        private Integer ddosUdpPps = 10000;

        /** DDoS ICMP Flood判定阈值（每秒包数） */
        @JsonProperty("ddos_icmp_pps")
        @Schema(description = "ICMP Flood每秒包数阈值")
        private Integer ddosIcmpPps = 5000;

        /** DDoS流量判定阈值（Mbps） */
        @JsonProperty("ddos_traffic_mbps")
        @Schema(description = "DDoS流量阈值（Mbps）")
        private Integer ddosTrafficMbps = 100;

        /** 流量基线计算窗口（秒） */
        @JsonProperty("traffic_baseline_window")
        @Schema(description = "流量基线计算窗口（秒）")
        private Integer trafficBaselineWindow = 600;

        /** 异常流量突发倍数，超过基线流量的此倍数判定为异常 */
        @JsonProperty("traffic_burst_baseline_multiplier")
        @Schema(description = "异常流量突发基线倍数")
        private Double trafficBurstBaselineMultiplier = 2.0;

        /** Web攻击检测轮询间隔（秒） */
        @JsonProperty("web_attack_check_interval")
        @Schema(description = "Web攻击检测间隔（秒）")
        private Integer webAttackCheckInterval = 10;

        /** Web攻击告警冷却时间（秒），同IP同类型不重复告警 */
        @JsonProperty("web_attack_cooldown")
        @Schema(description = "Web攻击告警冷却时间（秒）")
        private Integer webAttackCooldown = 60;

        /** Web日志每次增量读取的最大字节数 */
        @JsonProperty("web_attack_log_tail_size")
        @Schema(description = "Web日志增量读取最大字节数")
        private Integer webAttackLogTailSize = 65536;
    }

    // =========================================================================
    // settings.payload_sniffer — Payload嗅探配置
    // =========================================================================

    @Data
    @Schema(description = "Payload嗅探配置")
    public static class PayloadSniffer {

        /** 是否启用Payload嗅探 */
        @Schema(description = "是否启用")
        private Boolean enabled = true;

        /** 监听端口列表 */
        @Schema(description = "监听端口列表")
        private List<Integer> ports = new ArrayList<>(Arrays.asList(80, 443, 8080, 8443));

        /** 检测事件上报间隔（秒） */
        @JsonProperty("upload_interval")
        @Schema(description = "上报间隔（秒）")
        private Integer uploadInterval = 10;

        /** 单个Payload最大分析大小（字节） */
        @JsonProperty("max_payload_size")
        @Schema(description = "单个Payload最大大小（字节）")
        private Integer maxPayloadSize = 4096;

        /** 待上报事件队列最大容量 */
        @JsonProperty("event_queue_max")
        @Schema(description = "事件队列最大容量")
        private Integer eventQueueMax = 1000;

        /** 冷却时间（秒），同IP同类型不重复上报 */
        @Schema(description = "冷却时间（秒）")
        private Integer cooldown = 60;
    }

    // =========================================================================
    // settings.process_monitor — 进程监控配置
    // =========================================================================

    @Data
    @Schema(description = "进程监控配置")
    public static class ProcessMonitor {

        /** 是否启用进程监控 */
        @Schema(description = "是否启用")
        private Boolean enabled = true;

        /** 进程扫描间隔（秒） */
        @JsonProperty("scan_interval")
        @Schema(description = "扫描间隔（秒）")
        private Integer scanInterval = 5;

        /** 冷却时间（秒） */
        @Schema(description = "冷却时间（秒）")
        private Integer cooldown = 300;
    }

    // =========================================================================
    // settings.ip_blocker — IP拉黑配置
    // =========================================================================

    @Data
    @Schema(description = "IP拉黑配置")
    public static class IpBlocker {

        /** 是否启用IP自动拉黑 */
        @Schema(description = "是否启用")
        private Boolean enabled = false;

        /** 白名单同步间隔（秒） */
        @JsonProperty("whitelist_sync_interval")
        @Schema(description = "白名单同步间隔（秒）")
        private Integer whitelistSyncInterval = 300;

        /** 是否封禁出站连接 */
        @JsonProperty("block_outbound")
        @Schema(description = "是否封禁出站连接")
        private Boolean blockOutbound = false;

        /** 触发封禁的最低攻击级别（low/medium/high） */
        @JsonProperty("min_attack_level")
        @Schema(description = "最低攻击级别（low/medium/high）")
        private String minAttackLevel = "low";

        /** 防火墙规则名称前缀 */
        @JsonProperty("rule_name_prefix")
        @Schema(description = "防火墙规则名称前缀")
        private String ruleNamePrefix = "SafeClient_Block_";
    }
}
