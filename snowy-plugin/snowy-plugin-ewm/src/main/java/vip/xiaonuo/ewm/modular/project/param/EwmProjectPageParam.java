package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

/**
 * 项目表查询参数
 *
 * @author Richai
 * @date  2025/12/24 15:01
 **/
@Getter
@Setter
public class EwmProjectPageParam {

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

    /** 项目名称 */
    @Schema(description = "项目名称")
    private String projectName;

    /** 项目负责人 */
    @Schema(description = "项目负责人")
    private String projectLeader;

    /** 项目二维码 */
    @Schema(description = "项目状态")
    private String projectStatus;

    /** 项目附件 */
    @Schema(description = "所属机构")
    private String orgId;

    @Schema(description = "项目分类")
    private String projectType;

    @Schema(description = "所属客户")
    private String clientId;



}
