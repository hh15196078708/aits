package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class EwmProjectSafePageParam {
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
    @Schema(description = "排序方式，升序：ASCEND；降序：DESCEND")
    private String sortOrder;

    /** 关键词 */
    @Schema(description = "关键词")
    private String searchKey;

    private String projectId;

    private String safeIp;
}
