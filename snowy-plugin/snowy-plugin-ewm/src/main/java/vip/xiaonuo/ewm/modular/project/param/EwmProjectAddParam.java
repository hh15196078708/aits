package vip.xiaonuo.ewm.modular.project.param;

import com.alibaba.excel.annotation.format.DateTimeFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.util.Date;

/**
 * 项目表添加参数
 *
 * @author Richai
 * @date  2025/12/24 15:01
 **/
@Getter
@Setter
public class EwmProjectAddParam {
    /** 项目名称 */
    @Schema(description = "项目名称", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "项目名称不能为空")
    private String projectName;

    /** 项目负责人 */
    @Schema(description = "项目负责人", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "项目负责人不能为空")
    private String projectLeader;

    @Schema(description = "项目负责人", requiredMode = Schema.RequiredMode.REQUIRED)
    private String projectLeaderPhone;

    /** 排序码 */
    @Schema(description = "排序码")
    private Integer sortCode;

    /** 扩展信息 */
    @Schema(description = "扩展信息")
    private String extJson;

    /** 机构id */
    @Schema(description = "机构id", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "机构不能为空")
    private String orgId;

    /** 项目状态，WAIT-待开始,LOADING-进行中,OPERATION-运维中,STOP-项目结束 */
    @Schema(description = "项目状态", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "项目状态不能为空")
    private String projectStatus;

    /** 项目类别，integration-系统集成，develop-开发，safe-安全 */
    @Schema(description = "项目类别")
    @NotBlank(message = "项目类别不能为空")
    private String projectType;

    /** 项目金额 */
    @Schema(description = "项目金额")
    private BigDecimal projectMoney;

    /** 项目开始日期 */
    @DateTimeFormat("yyyy-MM-dd")
    @Schema(description = "项目开始日期")
    private String projectStartTime;

    /** 项目结束日期 */
    @DateTimeFormat("yyyy-MM-dd")
    @Schema(description = "项目结束日期")
    private String projectEndTime;

    /** 项目说明 */
    @Schema(description = "项目说明")
    private String projectDesc;

    /** 项目二维码 */
    @Schema(description = "项目二维码")
    private String projectEwm;

    /** 项目附件 */
    @Schema(description = "项目附件")
    private String projectFiles;
}
