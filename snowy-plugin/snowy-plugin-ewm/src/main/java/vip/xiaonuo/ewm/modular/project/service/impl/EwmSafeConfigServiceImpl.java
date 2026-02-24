package vip.xiaonuo.ewm.modular.project.service.impl;

import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.springframework.stereotype.Service;
import vip.xiaonuo.ewm.modular.project.entity.EwmSafeConfig;
import vip.xiaonuo.ewm.modular.project.mapper.EwmSafeConfigMapper;
import vip.xiaonuo.ewm.modular.project.param.EwmSafeConfigParam;
import vip.xiaonuo.ewm.modular.project.service.EwmSafeConfigService;

import java.util.List;

/**
 * 终端安全配置Service实现类
 *
 * @author Richai
 * @date 2026/02/24
 */
@Service
public class EwmSafeConfigServiceImpl extends ServiceImpl<EwmSafeConfigMapper, EwmSafeConfig> implements EwmSafeConfigService {

    @Override
    public void saveConfig(EwmSafeConfigParam param) {
        // 根据 safeId 查询是否已存在配置
        EwmSafeConfig existing = getConfigBySafeId(param.getSafeId());

        EwmSafeConfig config;
        if (ObjectUtil.isNotEmpty(existing)) {
            config = existing;
        } else {
            config = new EwmSafeConfig();
            config.setSafeId(param.getSafeId());
        }

        // 设置配置项
        if (param.getIpBlockerEnabled() != null) {
            config.setIpBlockerEnabled(param.getIpBlockerEnabled());
        }
        if (param.getIpWhitelist() != null) {
            config.setIpWhitelist(JSONUtil.toJsonStr(param.getIpWhitelist()));
        }
        if (param.getWebLogSources() != null) {
            config.setWebLogSources(JSONUtil.toJsonStr(param.getWebLogSources()));
        }
        if (param.getSnifferPorts() != null) {
            config.setSnifferPorts(JSONUtil.toJsonStr(param.getSnifferPorts()));
        }
        if (param.getSnifferEnabled() != null) {
            config.setSnifferEnabled(param.getSnifferEnabled());
        }
        if (param.getAttackLogUploadInterval() != null) {
            config.setAttackLogUploadInterval(param.getAttackLogUploadInterval());
        }

        this.saveOrUpdate(config);
    }

    @Override
    public EwmSafeConfig getConfigBySafeId(String safeId) {
        LambdaQueryWrapper<EwmSafeConfig> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(EwmSafeConfig::getSafeId, safeId);
        return this.getOne(queryWrapper);
    }

    @Override
    public String generateConfigJson(String safeId) {
        EwmSafeConfig config = getConfigBySafeId(safeId);

        // 构建完整的 client_config.json 结构，使用默认值
        JSONObject root = new JSONObject(true);

        // 运行时字段（使用默认空值）
        JSONObject authCache = new JSONObject(true);
        authCache.set("status", "normal");
        authCache.set("update_time", 0);
        root.set("auth_cache", authCache);

        root.set("auth_key", "");
        root.set("blocked_ips", new JSONArray());
        root.set("client_id", "");
        root.set("expire_time", "");
        root.set("first_run_time", null);

        JSONObject ipInfo = new JSONObject(true);
        ipInfo.set("external_ip", null);
        ipInfo.set("internal_ip", "");
        ipInfo.set("source", "psutil");
        root.set("ip_info", ipInfo);

        // IP白名单
        if (config != null && StrUtil.isNotEmpty(config.getIpWhitelist())) {
            root.set("ip_whitelist", JSONUtil.parseArray(config.getIpWhitelist()));
        } else {
            root.set("ip_whitelist", new JSONArray());
        }

        root.set("last_heartbeat_time", 0);
        root.set("machine_code", "");
        root.set("machine_name", "");

        JSONObject osInfo = new JSONObject(true);
        osInfo.set("arch", "64bit");
        osInfo.set("hostname", "");
        osInfo.set("kernel", "");
        osInfo.set("type", "Windows");
        osInfo.set("version", "");
        root.set("os_info", osInfo);

        // settings 部分
        JSONObject settings = new JSONObject(true);

        // attack_detection
        JSONObject attackDetection = new JSONObject(true);
        attackDetection.set("attack_detector_max_restart", 10);
        attackDetection.set("attack_detector_restart_delay", 3);
        attackDetection.set("attack_log_batch_size", 50);
        // 使用用户配置的上报间隔或默认30
        attackDetection.set("attack_log_upload_interval",
                config != null && config.getAttackLogUploadInterval() != null ? config.getAttackLogUploadInterval() : 30);
        attackDetection.set("rule_lib_backup_path", "data/rule_lib.backup.json");
        attackDetection.set("rule_lib_file_path", "data/rule_lib.json");
        attackDetection.set("rule_lib_sync_interval", 600);

        JSONObject thresholds = new JSONObject(true);
        thresholds.set("brute_force_fail_count", 5);
        thresholds.set("brute_force_time_window", 60);
        thresholds.set("ddos_icmp_pps", 5000);
        thresholds.set("ddos_syn_connections", 1000);
        thresholds.set("ddos_traffic_mbps", 100);
        thresholds.set("ddos_udp_pps", 10000);
        thresholds.set("port_scan_port_count", 20);
        thresholds.set("port_scan_time_window", 10);
        thresholds.set("traffic_baseline_window", 600);
        thresholds.set("traffic_burst_baseline_multiplier", 2.0);
        thresholds.set("web_attack_check_interval", 10);
        thresholds.set("web_attack_cooldown", 60);
        thresholds.set("web_attack_log_tail_size", 65536);
        attackDetection.set("thresholds", thresholds);

        attackDetection.set("traffic_baseline_samples", 100);
        attackDetection.set("traffic_collect_interval", 0.1);
        attackDetection.set("traffic_queue_max_size", 10000);
        settings.set("attack_detection", attackDetection);

        // auth
        JSONObject auth = new JSONObject(true);
        auth.set("cache_ttl", 300);
        auth.set("offline_grace_period", 600);
        settings.set("auth", auth);

        // crypto
        JSONObject crypto = new JSONObject(true);
        crypto.set("aes_block_size", 16);
        crypto.set("aes_key_length", 128);
        settings.set("crypto", crypto);

        // hardware
        JSONObject hardware = new JSONObject(true);
        hardware.set("cpu_usage_sample_interval", 0.5);
        hardware.set("machine_id_file", ".machine_id");
        settings.set("hardware", hardware);

        // heartbeat
        JSONObject heartbeat = new JSONObject(true);
        heartbeat.set("interval", 15);
        heartbeat.set("max_retry", 5);
        heartbeat.set("request_timeout", 5);
        heartbeat.set("retry_interval", 1);
        settings.set("heartbeat", heartbeat);

        // ip_blocker
        JSONObject ipBlocker = new JSONObject(true);
        ipBlocker.set("enabled",
                config != null && config.getIpBlockerEnabled() != null ? config.getIpBlockerEnabled() : false);
        ipBlocker.set("whitelist_sync_interval", 300);
        ipBlocker.set("block_outbound", false);
        ipBlocker.set("min_attack_level", "low");
        ipBlocker.set("rule_name_prefix", "SafeClient_Block_");
        settings.set("ip_blocker", ipBlocker);

        // logging
        JSONObject logging = new JSONObject(true);
        logging.set("backup_count", 5);
        logging.set("buffer_size", 1024);
        logging.set("file_prefix", "client");
        logging.set("level", "INFO");
        logging.set("max_size", 10485760);
        settings.set("logging", logging);

        // payload_sniffer
        JSONObject payloadSniffer = new JSONObject(true);
        payloadSniffer.set("cooldown", 60);
        payloadSniffer.set("enabled",
                config != null && config.getSnifferEnabled() != null ? config.getSnifferEnabled() : true);
        payloadSniffer.set("event_queue_max", 1000);
        payloadSniffer.set("max_payload_size", 4096);
        // 嗅探端口
        if (config != null && StrUtil.isNotEmpty(config.getSnifferPorts())) {
            payloadSniffer.set("ports", JSONUtil.parseArray(config.getSnifferPorts()));
        } else {
            payloadSniffer.set("ports", JSONUtil.parseArray("[80,443,8080,8443]"));
        }
        payloadSniffer.set("upload_interval", 10);
        settings.set("payload_sniffer", payloadSniffer);

        // resources
        JSONObject resources = new JSONObject(true);
        resources.set("cpu_avg_limit", 5);
        resources.set("cpu_peak_limit", 8);
        resources.set("cpu_sample_interval", 5);
        resources.set("cpu_throttle_sleep", 0.1);
        resources.set("cpu_throttle_threshold", 7);
        resources.set("disk_io_avg_limit", 1);
        resources.set("disk_io_peak_limit", 10);
        resources.set("disk_io_throttle_sleep", 0.5);
        resources.set("disk_io_throttle_threshold", 9);
        resources.set("memory_peak_limit", 300);
        resources.set("memory_resident_limit", 100);
        resources.set("memory_warning_threshold", 280);
        settings.set("resources", resources);

        // server
        JSONObject server = new JSONObject(true);
        JSONObject endpoints = new JSONObject(true);
        endpoints.set("attack_portscan", "/init/attack/portscan");
        endpoints.set("attack_threshold", "/attack/threshold/get");
        endpoints.set("attack_traffic", "/init/attack/traffic");
        endpoints.set("attack_web", "/init/attack/web");
        endpoints.set("detector_status", "/attack/detector/status");
        endpoints.set("heartbeat", "/init/check");
        endpoints.set("register", "/init/add");
        endpoints.set("rule_lib_update", "/attack/rule/update");
        endpoints.set("rule_lib_version", "/attack/rule/version");
        server.set("endpoints", endpoints);
        server.set("project_id", "2023031623403520002");
        server.set("url", "http://127.0.0.1:82/safe");
        settings.set("server", server);

        // storage
        JSONObject storage = new JSONObject(true);
        storage.set("config_dir_name", "client_config");
        storage.set("config_dir_name_unix", ".client_config");
        storage.set("config_file_name", "client_config.json");
        settings.set("storage", storage);

        root.set("settings", settings);

        // web_log_offsets
        root.set("web_log_offsets", new JSONObject());

        // web_log_sources
        if (config != null && StrUtil.isNotEmpty(config.getWebLogSources())) {
            root.set("web_log_sources", JSONUtil.parseArray(config.getWebLogSources()));
        } else {
            root.set("web_log_sources", new JSONArray());
        }

        return JSONUtil.toJsonPrettyStr(root);
    }
}
