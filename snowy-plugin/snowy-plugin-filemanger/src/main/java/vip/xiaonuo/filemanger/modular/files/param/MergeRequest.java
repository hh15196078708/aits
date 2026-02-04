package vip.xiaonuo.filemanger.modular.files.param;

import lombok.Data;

@Data
public class MergeRequest {
    private String hash;      // 文件唯一标识
    private String fileName;  // 原始文件名
    private String parentId;  // 父级文件夹ID
}
