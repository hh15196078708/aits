package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

import java.util.Date;

/**
 * 网络安全的客户端添加参数
 *
 * @author Richai
 * @date  2026/02/09 15:57
 **/
@Getter
@Setter
public class EwmProjectSafeAddParam {

    /** 所属项目 */
    @Schema(description = "所属项目")
    private String projectId;

    /** 秘钥 */
    @Schema(description = "秘钥")
    private String safeSecret;

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

}
