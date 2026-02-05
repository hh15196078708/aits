package vip.xiaonuo.filemanger.modular.files.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;
import java.math.BigDecimal;
import java.util.Date;

/**
 * 文件管理表实体
 *
 * @author Richai
 * @date  2026/01/30 17:35
 **/
@Getter
@Setter
@TableName("sys_files")
public class SysFiles {

    /** ID */
    @TableId
    @Schema(description = "ID")
    private String id;

    /** 父级ID，根目录为NULL */
    @Schema(description = "父级ID，根目录为0")
    private String parentId;

    /** 文件/文件夹名称 */
    @Schema(description = "文件/文件夹名称")
    private String name;

    /** 是否为文件夹: 0-否, 1-是 */
    @Schema(description = "是否为文件夹: 0-否, 1-是")
    private Boolean isFolder;

    /** 文件大小(字节) */
    @Schema(description = "文件大小(字节)")
    private Long fileSize;

    /** 物理存储路径 (仅文件) */
    @Schema(description = "物理存储路径 (仅文件)")
    private String filePath;

    /** MIME类型 */
    @Schema(description = "MIME类型")
    private String contentType;

    /** 排序码 */
    @Schema(description = "排序码")
    private Integer sortCode;

    /** 扩展信息 */
    @Schema(description = "扩展信息")
    private String extJson;

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

    /** 文件MD5 */
    @Schema(description = "文件MD5")
    private String fileMd5;

    /** 文件类型 */
    @Schema(description = "文件类型")
    private String fileType;
}
