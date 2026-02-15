package vip.xiaonuo.ewm.modular.project.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

import java.util.Date;

@Getter
@Setter
@TableName("ewm_project_safe")
public class EwmProjectSafeList {
    /** ID */
    @TableId
    @Schema(description = "ID")
    private String id;

    /** 创建时间 */
    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createTime;

    /** 所属项目 */
    @Schema(description = "所属项目")
    private String projectId;

    @Schema(description = "项目名称")
    private String projectName;

    /** 名称 */
    @Schema(description = "名称")
    private String safeName;

    /** 机器码 */
    @Schema(description = "机器码")
    private String safeCode;

    /** 操作系统 */
    @Schema(description = "操作系统")
    private String safeOs;

    /** IP地址 */
    @Schema(description = "IP地址")
    private String safeIp;

    /** 状态，ON-在线，OFF离线 */
    @Schema(description = "状态，ON-在线，OFF离线")
    private String safeStatus;

    /** 授权开始时间 */
    @Schema(description = "授权开始时间")
    private Date safeStartTime;

    /** 授权结束时间 */
    @Schema(description = "授权结束时间")
    private Date safeEndTime;

    private String safeCpu;

    //SAFE_CPU_USAGE
    private String safeCpuUsage;

    //SAFE_MEMORY
    private String safeMemory;

    private String safeMemoryUsage;

    private String safeDisk;

    //SAFE_DISK_USAGE
    private String safeDiskUsage;
}
