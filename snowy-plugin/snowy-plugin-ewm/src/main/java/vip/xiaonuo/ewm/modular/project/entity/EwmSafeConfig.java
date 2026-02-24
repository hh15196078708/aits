package vip.xiaonuo.ewm.modular.project.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

import java.util.Date;

/**
 * 终端安全配置实体
 *
 * @author Richai
 * @date 2026/02/24
 */
@Getter
@Setter
@TableName("ewm_safe_config")
public class EwmSafeConfig {

    /** 主键ID */
    @TableId
    @Schema(description = "主键ID")
    private String id;

    /** 终端设备ID */
    @Schema(description = "终端设备ID（关联ewm_project_safe.id）")
    private String safeId;

    /** 是否开启IP自动拉黑 */
    @Schema(description = "是否开启IP自动拉黑（0-关闭，1-开启）")
    private Boolean ipBlockerEnabled;

    /** IP白名单（JSON数组字符串） */
    @Schema(description = "IP白名单（JSON数组字符串）")
    private String ipWhitelist;

    /** Web日志存放路径（JSON数组字符串） */
    @Schema(description = "Web日志存放路径（JSON数组字符串）")
    private String webLogSources;

    /** 流量嗅探端口（JSON数组字符串） */
    @Schema(description = "流量嗅探端口（JSON数组字符串）")
    private String snifferPorts;

    /** 是否开启流量嗅探抓包 */
    @Schema(description = "是否开启流量嗅探抓包（0-关闭，1-开启）")
    private Boolean snifferEnabled;

    /** 攻击日志上报间隔（秒） */
    @Schema(description = "攻击日志上报间隔（秒）")
    private Integer attackLogUploadInterval;

    /** 删除标志 */
    @Schema(description = "删除标志")
    @TableLogic
    @TableField(fill = FieldFill.INSERT)
    private String deleteFlag;

    /** 创建时间 */
    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createTime;

    /** 创建用户 */
    @Schema(description = "创建用户")
    @TableField(fill = FieldFill.INSERT)
    private String createUser;

    /** 修改时间 */
    @Schema(description = "修改时间")
    @TableField(fill = FieldFill.UPDATE)
    private Date updateTime;

    /** 修改用户 */
    @Schema(description = "修改用户")
    @TableField(fill = FieldFill.UPDATE)
    private String updateUser;
}
