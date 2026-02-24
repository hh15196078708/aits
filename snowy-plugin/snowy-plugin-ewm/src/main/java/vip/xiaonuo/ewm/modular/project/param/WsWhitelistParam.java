package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class WsWhitelistParam {

    @Schema(description = "终端ID", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "终端ID不能为空")
    private String clientId;

    @Schema(description = "IP白名单列表（支持IP和CIDR）", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotNull(message = "ips不能为空")
    private List<String> ips;
}
