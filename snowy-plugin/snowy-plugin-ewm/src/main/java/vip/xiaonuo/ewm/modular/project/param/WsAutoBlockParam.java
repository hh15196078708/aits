package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class WsAutoBlockParam {

    @Schema(description = "终端ID", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "终端ID不能为空")
    private String clientId;

    @Schema(description = "是否开启自动拉黑", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotNull(message = "enabled不能为空")
    private Boolean enabled;
}
