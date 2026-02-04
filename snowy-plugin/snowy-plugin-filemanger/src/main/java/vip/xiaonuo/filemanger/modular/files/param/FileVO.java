package vip.xiaonuo.filemanger.modular.files.param;

import lombok.Data;
import vip.xiaonuo.filemanger.modular.files.entity.SysFiles;

import java.text.SimpleDateFormat;
import java.time.format.DateTimeFormatter;
import java.util.Date;

@Data
public class FileVO {
    private String id;
    private String name;
    private String type; // 前端需要 'file' 或 'folder'
    private String size; // 前端需要格式化好的字符串，如 "2.5 MB"
    private String updatedAt;
    private String parentId;

    // 静态工厂方法：将 Entity 转换为 VO
    public static FileVO fromEntity(SysFiles entity) {
        FileVO vo = new FileVO();
        vo.setId(entity.getId());
        vo.setName(entity.getName());
        vo.setParentId(entity.getParentId());

        // 转换类型
        vo.setType(entity.getIsFolder() ? "folder" : "file");

        // 转换时间格式
        if (entity.getUpdateTime() != null) {
            SimpleDateFormat formatter = new SimpleDateFormat("yyyy-MM-dd HH:mm");
            String formattedDate = formatter.format(entity.getUpdateTime()); // 直接格式化实体的时间字段
            vo.setUpdatedAt(formattedDate);
        }

        // 转换大小 (如果是文件夹显示 "-")
        if (entity.getIsFolder()) {
            vo.setSize("-");
        } else {
            vo.setSize(formatSize(entity.getFileSize()));
        }
        return vo;
    }

    // 辅助方法：字节转可读大小
    private static String formatSize(Long size) {
        if (size == null) return "0 B";
        if (size < 1024) return size + " B";
        int exp = (int) (Math.log(size) / Math.log(1024));
        String pre = "KMGTPE".charAt(exp - 1) + "";
        return String.format("%.1f %sB", size / Math.pow(1024, exp), pre);
    }
}
