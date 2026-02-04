package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;

/**
 * 项目表Id参数
 *
 * @author Richai
 * @date  2025/12/24 15:01
 **/
@Getter
@Setter
public class EwmProjectIdParam {

    /** ID */
    @Schema(description = "ID")
    @NotBlank(message = "id不能为空")
    private String id;
}
