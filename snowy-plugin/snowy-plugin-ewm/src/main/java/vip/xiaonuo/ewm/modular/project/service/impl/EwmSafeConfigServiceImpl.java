package vip.xiaonuo.ewm.modular.project.service.impl;

import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import jakarta.annotation.Resource;
import org.springframework.stereotype.Service;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafe;
import vip.xiaonuo.ewm.modular.project.param.EwmSafeConfigParam;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectSafeService;
import vip.xiaonuo.ewm.modular.project.service.EwmSafeConfigService;

import java.util.HashMap;
import java.util.Map;

/**
 * 终端安全配置Service实现类
 * <p>
 * 配置以JSON字符串形式存储在 ewm_project_safe.config_json 字段中。
 * 前端提交完整配置对象，后端直接序列化存储；
 * 生成 client_config.json 时，以内置默认值为底，将存储的配置深度合并覆盖。
 *
 * @author Richai
 * @date 2026/02/24
 */
@Service
public class EwmSafeConfigServiceImpl implements EwmSafeConfigService {

    @Resource
    private EwmProjectSafeService ewmProjectSafeService;

    @Override
    public void saveConfig(EwmSafeConfigParam param) {
        EwmProjectSafe safe = ewmProjectSafeService.getById(param.getSafeId());
        if (ObjectUtil.isEmpty(safe)) {
            throw new RuntimeException("终端设备不存在");
        }
        Map<String, Object> config = param.getConfig();
        safe.setConfigJson(config != null ? JSONUtil.toJsonStr(config) : "{}");
        ewmProjectSafeService.updateById(safe);
    }

    @Override
    public Map<String, Object> getConfigBySafeId(String safeId) {
        EwmProjectSafe safe = ewmProjectSafeService.getById(safeId);
        if (ObjectUtil.isEmpty(safe) || StrUtil.isEmpty(safe.getConfigJson())) {
            return new HashMap<>();
        }
        try {
            return JSONUtil.parseObj(safe.getConfigJson());
        } catch (Exception e) {
            return new HashMap<>();
        }
    }

    // =========================================================================
    // 生成完整 client_config.json（用于下载）
    // =========================================================================

    @Override
    public String generateConfigJson(String safeId) {
        Map<String, Object> stored = getConfigBySafeId(safeId);

        JSONObject root = new JSONObject(true);

        // ---- 运行时字段（空占位，客户端启动后自动填充） ----
        root.set("auth_cache", new JSONObject(true).set("status", "normal").set("update_time", 0));
        root.set("auth_key", "");
        root.set("blocked_ips", new JSONArray());
        root.set("client_id", "");
        root.set("expire_time", "");
        root.set("first_run_time", null);
        root.set("ip_info", new JSONObject(true).set("external_ip", null).set("internal_ip", "").set("source", "psutil"));
        root.set("ip_whitelist", getStored(stored, "ipWhitelist", new JSONArray()));
        root.set("last_heartbeat_time", 0);
        root.set("machine_code", "");
        root.set("machine_name", "");
        root.set("os_info", new JSONObject(true).set("arch", "64bit").set("hostname", "").set("kernel", "").set("type", "Windows").set("version", ""));

        // ---- settings：内置默认 + 存储值深度合并 ----
        JSONObject settings = buildDefaultSettings();
        deepMergeFromStored(settings, stored);
        root.set("settings", settings);

        // ---- 顶层可配置字段 ----
        root.set("web_log_offsets", new JSONObject());
        root.set("web_log_sources", getStored(stored, "webLogSources", new JSONArray()));

        return JSONUtil.toJsonPrettyStr(root);
    }

    // =========================================================================
    // 构建完整的 settings 默认值（与客户端 constants.py _DEFAULTS 一致）
    // =========================================================================

    private JSONObject buildDefaultSettings() {
        JSONObject s = new JSONObject(true);

        // attack_detection
        JSONObject ad = new JSONObject(true);
        ad.set("attack_detector_max_restart", 10);
        ad.set("attack_detector_restart_delay", 3);
        ad.set("attack_log_batch_size", 50);
        ad.set("attack_log_upload_interval", 30);
        ad.set("rule_lib_backup_path", "data/rule_lib.backup.json");
        ad.set("rule_lib_file_path", "data/rule_lib.json");
        ad.set("rule_lib_sync_interval", 600);
        JSONObject th = new JSONObject(true);
        th.set("brute_force_fail_count", 5);
        th.set("brute_force_time_window", 60);
        th.set("ddos_icmp_pps", 5000);
        th.set("ddos_syn_connections", 1000);
        th.set("ddos_traffic_mbps", 100);
        th.set("ddos_udp_pps", 10000);
        th.set("port_scan_port_count", 20);
        th.set("port_scan_time_window", 10);
        th.set("traffic_baseline_window", 600);
        th.set("traffic_burst_baseline_multiplier", 2.0);
        th.set("web_attack_check_interval", 10);
        th.set("web_attack_cooldown", 60);
        th.set("web_attack_log_tail_size", 65536);
        ad.set("thresholds", th);
        ad.set("traffic_baseline_samples", 100);
        ad.set("traffic_collect_interval", 0.1);
        ad.set("traffic_queue_max_size", 10000);
        s.set("attack_detection", ad);

        // auth
        s.set("auth", new JSONObject(true).set("cache_ttl", 300).set("offline_grace_period", 600));

        // crypto
        s.set("crypto", new JSONObject(true).set("aes_block_size", 16).set("aes_key_length", 128));

        // hardware
        s.set("hardware", new JSONObject(true).set("cpu_usage_sample_interval", 0.5).set("machine_id_file", ".machine_id"));

        // heartbeat
        s.set("heartbeat", new JSONObject(true).set("interval", 15).set("max_retry", 5).set("request_timeout", 5).set("retry_interval", 1));

        // ip_blocker
        JSONObject ib = new JSONObject(true);
        ib.set("block_outbound", false);
        ib.set("enabled", false);
        ib.set("min_attack_level", "low");
        ib.set("rule_name_prefix", "SafeClient_Block_");
        ib.set("whitelist_sync_interval", 300);
        s.set("ip_blocker", ib);

        // logging
        s.set("logging", new JSONObject(true).set("backup_count", 5).set("buffer_size", 1024).set("file_prefix", "client").set("level", "INFO").set("max_size", 10485760));

        // payload_sniffer
        JSONObject ps = new JSONObject(true);
        ps.set("cooldown", 60);
        ps.set("enabled", true);
        ps.set("event_queue_max", 1000);
        ps.set("max_payload_size", 4096);
        ps.set("ports", JSONUtil.parseArray("[80,443,8080,8443]"));
        ps.set("upload_interval", 10);
        s.set("payload_sniffer", ps);

        // process_monitor
        s.set("process_monitor", new JSONObject(true).set("enabled", true).set("scan_interval", 5).set("cooldown", 300));

        // resources
        JSONObject res = new JSONObject(true);
        res.set("cpu_avg_limit", 5);
        res.set("cpu_peak_limit", 8);
        res.set("cpu_sample_interval", 5);
        res.set("cpu_throttle_sleep", 0.1);
        res.set("cpu_throttle_threshold", 7);
        res.set("disk_io_avg_limit", 1);
        res.set("disk_io_peak_limit", 10);
        res.set("disk_io_throttle_sleep", 0.5);
        res.set("disk_io_throttle_threshold", 9);
        res.set("memory_peak_limit", 300);
        res.set("memory_resident_limit", 100);
        res.set("memory_warning_threshold", 280);
        s.set("resources", res);

        // server
        JSONObject srv = new JSONObject(true);
        JSONObject ep = new JSONObject(true);
        ep.set("attack_portscan", "/init/attack/portscan");
        ep.set("attack_threshold", "/attack/threshold/get");
        ep.set("attack_traffic", "/init/attack/traffic");
        ep.set("attack_web", "/init/attack/web");
        ep.set("detector_status", "/attack/detector/status");
        ep.set("heartbeat", "/init/check");
        ep.set("register", "/init/add");
        ep.set("rule_lib_update", "/attack/rule/update");
        ep.set("rule_lib_version", "/attack/rule/version");
        srv.set("endpoints", ep);
        srv.set("project_id", "2023031623403520002");
        srv.set("url", "http://127.0.0.1:82/safe");
        s.set("server", srv);

        // storage
        s.set("storage", new JSONObject(true).set("config_dir_name", "client_config").set("config_dir_name_unix", ".client_config").set("config_file_name", "client_config.json"));

        // websocket
        s.set("websocket", new JSONObject(true).set("url", "ws://127.0.0.1:82/safe/init/ws").set("reconnect_interval", 5).set("ssl_verify", true));

        return s;
    }

    // =========================================================================
    // 工具方法
    // =========================================================================

    /**
     * 将前端存储的配置深度合并进默认 settings。
     * stored 中 key 与 settings 子节同名的（如 server、heartbeat 等），递归合并；
     * ipWhitelist、webLogSources 等顶层字段不属于 settings，在外部单独处理。
     */
    @SuppressWarnings("unchecked")
    private void deepMergeFromStored(JSONObject defaults, Map<String, Object> stored) {
        String[] settingsKeys = {
                "server", "websocket", "heartbeat", "auth", "crypto", "hardware",
                "logging", "resources", "storage", "attack_detection",
                "payload_sniffer", "process_monitor", "ip_blocker"
        };
        for (String key : settingsKeys) {
            Object val = stored.get(key);
            if (val instanceof Map) {
                JSONObject defaultSection = defaults.getJSONObject(key);
                if (defaultSection != null) {
                    deepMerge(defaultSection, new JSONObject((Map<String, Object>) val));
                }
            }
        }
    }

    /**
     * 递归深度合并：override 中的值覆盖 base 中的同名键。
     */
    @SuppressWarnings("unchecked")
    private void deepMerge(JSONObject base, JSONObject override) {
        for (String key : override.keySet()) {
            Object overrideVal = override.get(key);
            Object baseVal = base.get(key);
            if (baseVal instanceof JSONObject && overrideVal instanceof Map) {
                deepMerge((JSONObject) baseVal, new JSONObject((Map<String, Object>) overrideVal));
            } else {
                base.set(key, overrideVal);
            }
        }
    }

    private Object getStored(Map<String, Object> stored, String key, Object defaultVal) {
        Object val = stored.get(key);
        return val != null ? val : defaultVal;
    }
}
