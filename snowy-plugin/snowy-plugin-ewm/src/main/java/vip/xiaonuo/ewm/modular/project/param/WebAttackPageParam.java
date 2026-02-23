package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class WebAttackPageParam {
    @Schema(description = "当前页")
    private Integer current = 1;

    @Schema(description = "每页大小")
    private Integer size = 10;

    @Schema(description = "终端ID")
    private String safeId;

    @Schema(description = "源IP")
    private String sourceIp;

    @Schema(description = "攻击类型")
    private String attackType;

    @Schema(description = "威胁等级")
    private String level;


}
