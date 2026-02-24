package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

/**
 * 终端安全配置参数
 *
 * @author Richai
 * @date 2026/02/24
 */
@Data
public class EwmSafeConfigParam {

    /** 终端设备ID */
    @Schema(description = "终端设备ID")
    @NotEmpty(message = "终端设备ID不能为空")
    private String safeId;

    /** 是否开启IP自动拉黑 */
    @Schema(description = "是否开启IP自动拉黑")
    private Boolean ipBlockerEnabled;

    /** IP白名单列表 */
    @Schema(description = "IP白名单列表")
    private List<String> ipWhitelist;

    /** Web日志源列表 */
    @Schema(description = "Web日志源列表")
    private List<WebLogSourceItem> webLogSources;

    /** 流量嗅探端口列表 */
    @Schema(description = "流量嗅探端口列表")
    private List<Integer> snifferPorts;

    /** 是否开启流量嗅探抓包 */
    @Schema(description = "是否开启流量嗅探抓包")
    private Boolean snifferEnabled;

    /** 攻击日志上报间隔（秒） */
    @Schema(description = "攻击日志上报间隔（秒）")
    private Integer attackLogUploadInterval;

    /**
     * Web日志源项
     */
    @Data
    public static class WebLogSourceItem {
        @Schema(description = "日志路径")
        private String path;

        @Schema(description = "日志类型（nginx/apache/iis/tomcat）")
        private String type;

        @Schema(description = "是否启用")
        private Boolean enabled;
    }
}
