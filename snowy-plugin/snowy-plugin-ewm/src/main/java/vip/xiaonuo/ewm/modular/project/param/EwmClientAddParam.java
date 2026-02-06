package vip.xiaonuo.ewm.modular.project.param;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class EwmClientAddParam {
    /** 客户名称 */
    @Schema(description = "客户名称", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "name不能为空")
    private String name;

    /** 经办人(多个逗号分隔) */
    @Schema(description = "经办人", requiredMode = Schema.RequiredMode.REQUIRED)
    private String agent;

    /** 联系电话(多个逗号分隔) */
    @Schema(description = "联系电话")
    private String phone;

    /** 单位地址 */
    @Schema(description = "单位地址")
    private String address;

    /** 经度 */
    @Schema(description = "经度")
    private String longitude;

    /** 纬度 */
    @Schema(description = "纬度")
    private String latitude;

    /** 备注 */
    @Schema(description = "备注")
    private String remark;

    /** 排序码 */
    @Schema(description = "排序码")
    private Integer sortCode;

    @Schema(description = "组织类型")
    @NotBlank(message = "组织类型不能为空")
    private String orgType;
}
