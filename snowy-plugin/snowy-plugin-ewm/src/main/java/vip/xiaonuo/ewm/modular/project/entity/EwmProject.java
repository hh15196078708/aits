package vip.xiaonuo.ewm.modular.project.entity;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;
import vip.xiaonuo.common.pojo.CommonEntity;

import java.math.BigDecimal;
import java.util.Date;

@Getter
@Setter
@TableName(value = "ewm_project", autoResultMap = true)
public class EwmProject extends CommonEntity {
    private static final long serialVersionUID = 1L;
    /** ID */
    @TableId
    @Schema(description = "ID")
    private String id;

    /** 项目名称 */
    @Schema(description = "项目名称")
    private String projectName;

    /** 项目负责人 */
    @Schema(description = "项目负责人")
    private String projectLeader;

    @Schema(description = "项目负责人电话")
    private String projectLeaderPhone;

    /** 排序码 */
    @Schema(description = "排序码")
    private Integer sortCode;

    /** 机构id */
    @Schema(description = "机构id")
    private String orgId;

    /** 项目状态，WAIT-待开始,LOADING-进行中,OPERATION-运维中,STOP-项目结束 */
    @Schema(description = "项目状态")
    private String projectStatus;

    /** 项目类别，integration-系统集成，develop-开发，safe-安全 */
    @Schema(description = "项目类别")
    private String projectType;

    /** 项目金额 */
    @Schema(description = "项目金额")
    private BigDecimal projectMoney;

    /** 项目开始日期 */
    @Schema(description = "项目开始日期")
    @JsonFormat(locale = "zh", timezone = "GMT+8", pattern = "yyyy-MM-dd")
    private Date projectStartTime;

    /** 项目结束日期 */
    @Schema(description = "项目结束日期")
    @JsonFormat(locale = "zh", timezone = "GMT+8", pattern = "yyyy-MM-dd")
    private Date projectEndTime;

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
