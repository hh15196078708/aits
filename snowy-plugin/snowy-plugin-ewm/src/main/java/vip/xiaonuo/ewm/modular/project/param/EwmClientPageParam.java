package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class EwmClientPageParam {
    /** 当前页 */
    @Schema(description = "当前页码")
    private Integer current;

    /** 每页条数 */
    @Schema(description = "每页条数")
    private Integer size;

    /** 排序字段 */
    @Schema(description = "排序字段，字段驼峰名称，如：userName")
    private String sortField;

    /** 排序方式 */
    @Schema(description = "排序方式，asc升序，desc降序")
    private String sortOrder;

    /** 客户名称 */
    @Schema(description = "客户名称")
    private String name;

    /** 经办人 */
    @Schema(description = "经办人")
    private String agent;

    /** 客户id */
    @Schema(description = "所属客户")
    private String clientId;
}
