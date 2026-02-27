package vip.xiaonuo.ewm.modular.project.service;

import vip.xiaonuo.ewm.modular.project.param.EwmSafeConfigParam;

import java.util.Map;

/**
 * 终端安全配置Service接口
 * <p>
 * 配置以JSON字符串形式存储在 ewm_project_safe.config_json 字段中，
 * 不再使用独立的 ewm_safe_config 表。
 *
 * @author Richai
 * @date 2026/02/24
 */
public interface EwmSafeConfigService {

    /**
     * 保存终端配置（以JSON形式写入 ewm_project_safe.config_json）
     */
    void saveConfig(EwmSafeConfigParam param);

    /**
     * 根据终端ID获取配置（从 ewm_project_safe.config_json 读取并解析）
     */
    Map<String, Object> getConfigBySafeId(String safeId);

    /**
     * 生成完整的 client_config.json 格式JSON字符串（用于下载）
     */
    String generateConfigJson(String safeId);
}
