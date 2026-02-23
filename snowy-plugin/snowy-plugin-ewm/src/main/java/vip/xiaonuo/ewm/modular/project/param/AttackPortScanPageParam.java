package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class AttackPortScanPageParam {
    @Schema(description = "当前页")
    private Integer current = 1;

    @Schema(description = "每页大小")
    private Integer size = 10;

    @Schema(description = "终端ID")
    private String safeId;

    @Schema(description = "源IP")
    private String sourceIp;

    @Schema(description = "扫描类型")
    private String scanType;

    @Schema(description = "威胁等级")
    private String level;
}
