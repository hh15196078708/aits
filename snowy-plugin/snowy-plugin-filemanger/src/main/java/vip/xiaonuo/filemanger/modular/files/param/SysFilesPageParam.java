package vip.xiaonuo.filemanger.modular.files.param;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class SysFilesPageParam {
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

    @Schema(description = "父级ID")
    private String parentId;

    @Schema(description = "搜索关键词（文件名称）")
    private String searchKeyword;

    @Schema(description = "是否是文件夹")
    private Integer isFolder;
}
