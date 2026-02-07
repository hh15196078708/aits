package vip.xiaonuo.ewm.modular.project.param;

import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.format.DateTimeFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.util.Date;

/**
 * 项目表编辑参数
 *
 * @author Richai
 * @date  2025/12/30 14:28
 **/
@Getter
@Setter
public class EwmProjectEditParam {

    /** ID */
    @ExcelProperty("ID")
    @Schema(description = "ID", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "id不能为空")
    private String id;

    /** 项目名称 */
    @ExcelProperty("项目名称")
    @Schema(description = "项目名称", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "项目名称不能为空")
    private String projectName;

    /** 项目负责人 */
    @ExcelProperty("项目负责人")
    @Schema(description = "项目负责人", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "项目负责人不能为空")
    private String projectLeader;

    @ExcelProperty("项目负责人联系方式")
    @Schema(description = "项目负责人联系方式", requiredMode = Schema.RequiredMode.REQUIRED)
    private String projectLeaderPhone;

    /** 排序码 */
    @ExcelProperty("排序码")
    @Schema(description = "排序码")
    private Integer sortCode;

    /** 扩展信息 */
    @ExcelProperty("扩展信息")
    @Schema(description = "扩展信息")
    private String extJson;

    /** 机构id */
    @ExcelProperty("机构id")
    @Schema(description = "机构id", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "所属机构不能为空")
    private String orgId;

    /** 项目状态，WAIT-待开始,LOADING-进行中,OPERATION-运维中,STOP-项目结束 */
    @ExcelProperty("项目状态")
    @Schema(description = "项目状态", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "项目状态不能为空")
    private String projectStatus;

    /** 项目类别，integration-系统集成，develop-开发，safe-安全 */
    @ExcelProperty("项目类别")
    @Schema(description = "项目类别")
    private String projectType;

    /** 项目金额 */
    @ExcelProperty("项目金额")
    @Schema(description = "项目金额")
    private BigDecimal projectMoney;

    /** 项目开始日期 */
    @DateTimeFormat("yyyy-MM-dd")
    @ExcelProperty("项目开始日期")
    @Schema(description = "项目开始日期")
    private String projectStartTime;

    /** 项目结束日期 */
    @DateTimeFormat("yyyy-MM-dd")
    @ExcelProperty("项目结束日期")
    @Schema(description = "项目结束日期")
    private String projectEndTime;

    /** 项目说明 */
    @ExcelProperty("项目说明")
    @Schema(description = "项目说明")
    private String projectDesc;

    @ExcelProperty("项目二维码")
    /** 项目二维码 */
    @Schema(description = "项目二维码")
    private String projectEwm;

    /** 项目附件 */
    @Schema(description = "项目附件")
    private String projectFiles;

    @Schema(description = "项目验收时间")
    @DateTimeFormat("yyyy-MM-dd")
    private Date projectAcceptTime;

    /** 客户id */
    @Schema(description = "所属客户")
    private String clientId;
}
