package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class WsClientIdParam {

    @Schema(description = "终端ID", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "终端ID不能为空")
    private String clientId;
}
