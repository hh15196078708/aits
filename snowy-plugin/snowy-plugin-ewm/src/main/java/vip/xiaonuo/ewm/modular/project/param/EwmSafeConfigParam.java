package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.Map;

/**
 * 终端安全配置参数
 * <p>
 * config 字段接收前端提交的完整配置对象（与 client_config.json 的 settings 结构对齐），
 * 后端直接序列化为 JSON 字符串存储到 ewm_project_safe.config_json 中。
 *
 * @author Richai
 * @date 2026/02/24
 */
@Data
public class EwmSafeConfigParam {

    /** 终端设备ID */
    @Schema(description = "终端设备ID")
    @NotEmpty(message = "终端设备ID不能为空")
    private String safeId;

    /** 完整配置对象（包含所有 settings 子节及 ipWhitelist、webLogSources 等可配置项） */
    @Schema(description = "完整配置对象")
    private Map<String, Object> config;
}
