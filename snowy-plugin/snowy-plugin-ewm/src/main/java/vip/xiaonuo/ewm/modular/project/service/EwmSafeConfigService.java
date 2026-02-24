package vip.xiaonuo.ewm.modular.project.service;

import com.baomidou.mybatisplus.extension.service.IService;
import vip.xiaonuo.ewm.modular.project.entity.EwmSafeConfig;
import vip.xiaonuo.ewm.modular.project.param.EwmSafeConfigParam;

/**
 * 终端安全配置Service接口
 *
 * @author Richai
 * @date 2026/02/24
 */
public interface EwmSafeConfigService extends IService<EwmSafeConfig> {

    /**
     * 保存终端配置（存在则更新，不存在则新增）
     */
    void saveConfig(EwmSafeConfigParam param);

    /**
     * 根据终端ID获取配置
     */
    EwmSafeConfig getConfigBySafeId(String safeId);

    /**
     * 生成完整的 client_config.json 格式JSON字符串
     */
    String generateConfigJson(String safeId);
}
