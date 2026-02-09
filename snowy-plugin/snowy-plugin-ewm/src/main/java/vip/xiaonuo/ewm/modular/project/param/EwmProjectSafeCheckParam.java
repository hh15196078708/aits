package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;

/**
 * 项目安全终端校验参数
 *
 * @author snowy
 * @date 2023/11/24 10:00
 */
@Getter
@Setter
public class EwmProjectSafeCheckParam {

    @Schema(description = "终端ID")
    @NotBlank(message = "id不能为空")
    private String id;

    @Schema(description = "所属项目ID")
    @NotBlank(message = "projectId不能为空")
    private String projectId;

    @Schema(description = "秘钥")
    @NotBlank(message = "safeSecret不能为空")
    private String safeSecret;

    @Schema(description = "机器码")
    @NotBlank(message = "safeCode不能为空")
    private String safeCode;
}
