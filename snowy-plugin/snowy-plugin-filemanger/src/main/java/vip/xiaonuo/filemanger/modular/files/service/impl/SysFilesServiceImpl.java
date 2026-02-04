package vip.xiaonuo.filemanger.modular.files.service.impl;


import cn.hutool.core.date.DateUtil;
import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.extra.spring.SpringUtil;
import cn.hutool.system.SystemUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import vip.xiaonuo.common.exception.CommonException;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.dev.api.DevConfigApi;
import vip.xiaonuo.dev.modular.file.enums.DevFileEngineTypeEnum;
import vip.xiaonuo.dev.modular.file.util.DevFileLocalUtil;
import vip.xiaonuo.filemanger.modular.files.entity.SysFiles;
import vip.xiaonuo.filemanger.modular.files.mapper.SysFilesMapper;
import vip.xiaonuo.filemanger.modular.files.param.FileVO;
import vip.xiaonuo.filemanger.modular.files.param.MergeRequest;
import vip.xiaonuo.filemanger.modular.files.service.SysFilesService;

import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 文件管理表Service接口实现类
 *
 * @author Richai
 * @date  2026/01/30 17:35
 **/
@Service
public class SysFilesServiceImpl extends ServiceImpl<SysFilesMapper, SysFiles> implements SysFilesService {

    private static final String SNOWY_FILE_LOCAL_FOLDER_FOR_WINDOWS_KEY = "SNOWY_FILE_LOCAL_FOLDER_FOR_WINDOWS";
    private static final String SNOWY_FILE_LOCAL_FOLDER_FOR_UNIX_KEY = "SNOWY_FILE_LOCAL_FOLDER_FOR_UNIX";

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void createFolder(SysFiles files) {
        //判断在当前目录下是否存在同名文件夹名称
        Long count = baseMapper.selectCount(
                new QueryWrapper<SysFiles>()
                        .eq("parent_id", files.getParentId())
                        .eq("name", files.getName())
                        .eq("is_folder", true)
                        .eq("DELETE_FLAG", "NOT_DELETE")
        );
        if (count > 0) {
            throw new RuntimeException("当前目录下已存在同名文件夹名称");
        }

        this.save(files);
    }

    @Override
    public CommonResult<String> uploadChunk(MultipartFile chunk, String hash, Integer index) throws IOException {
        String uploadFileFolder = getUploadPath();
        String tempDirPath = uploadFileFolder + File.separator + "temp" + File.separator + hash;
        File tempDir = new File(tempDirPath);
        if (!tempDir.exists()) {
            tempDir.mkdirs();
        }

        // 分片文件: uploadPath/temp/{hash}/{index}
        File chunkFile = new File(tempDir, String.valueOf(index));
        // 如果分片已存在，直接返回（支持断点续传）
        if (chunkFile.exists()) {
            return CommonResult.ok("skipped");
        }

        chunk.transferTo(chunkFile);
        return CommonResult.ok("success");
    }

    @Override
    public CommonResult<FileVO> mergeChunks(MergeRequest mergeRequest) throws IOException {
        String hash = mergeRequest.getHash();
        String fileName = mergeRequest.getFileName();
        String parentId = mergeRequest.getParentId();
        String uploadPath = getUploadPath();
        String tempDirPath = uploadPath + File.separator + "temp" + File.separator + hash;
        File tempDir = new File(tempDirPath);
        if (!tempDir.exists() || !tempDir.isDirectory()) {
            throw new RuntimeException("分片数据丢失");
        }

        // 2. 获取所有分片文件并按序号排序
        File[] chunkFiles = tempDir.listFiles();
        if (chunkFiles == null || chunkFiles.length == 0) {
            throw new RuntimeException("未找到分片文件");
        }

        List<File> sortedChunks = Arrays.stream(chunkFiles)
                .sorted(Comparator.comparingInt(f -> Integer.parseInt(f.getName())))
                .collect(Collectors.toList());

        // 3. 确定最终文件路径
        File uploadDir = new File(uploadPath);
        if (!uploadDir.exists()) uploadDir.mkdirs();
        String dateFolderPath = DateUtil.thisYear() + StrUtil.SLASH +
                (DateUtil.thisMonth() + 1) + StrUtil.SLASH +
                DateUtil.thisDayOfMonth() + StrUtil.SLASH;
        String suffix = fileName.contains(".") ? fileName.substring(fileName.lastIndexOf(".")) : "";
        String realFileName = UUID.randomUUID().toString() + suffix; // 避免重名
        Path targetPath = Paths.get(uploadPath+dateFolderPath, realFileName);
        // 4. 执行合并
        // 创建目标文件
        Files.createFile(targetPath);
        // 追加写入
        try (OutputStream os = Files.newOutputStream(targetPath, StandardOpenOption.APPEND)) {
            for (File chunk : sortedChunks) {
                Files.copy(chunk.toPath(), os);
            }
        }

        // 5. 清理临时分片
        for (File chunk : chunkFiles) {
            chunk.delete();
        }
        tempDir.delete();
// 6. 保存到数据库
        SysFiles sysFile = new SysFiles();
        sysFile.setName(fileName);
        sysFile.setParentId("null".equals(parentId) ? null : parentId);
        sysFile.setIsFolder(false);
        sysFile.setFileSize(Files.size(targetPath));
        sysFile.setFilePath(targetPath.toString());
        sysFile.setContentType(Files.probeContentType(targetPath));

        this.save(sysFile);

        FileVO fileVO = FileVO.fromEntity(sysFile);
        return CommonResult.data(fileVO);
    }

    public static String getUploadPath() {
        String uploadFileFolder;

        DevConfigApi devConfigApi = SpringUtil.getBean(DevConfigApi.class);

        if(SystemUtil.getOsInfo().isWindows()) {

            /* 本地文件上传的位置 windows系统 */
            String localFolderForWindows = devConfigApi.getValueByKey(SNOWY_FILE_LOCAL_FOLDER_FOR_WINDOWS_KEY);

            if(ObjectUtil.isEmpty(localFolderForWindows)) {
                throw new CommonException("本地文件操作客户端未正确配置：SNOWY_FILE_LOCAL_FOLDER_FOR_WINDOWS为空");
            }
            uploadFileFolder = localFolderForWindows;
        } else {
            /* 本地文件上传的位置 unix系列系统（linux、mac等） */
            String localFolderForUnix = devConfigApi.getValueByKey(SNOWY_FILE_LOCAL_FOLDER_FOR_UNIX_KEY);

            if(ObjectUtil.isEmpty(localFolderForUnix)) {
                throw new CommonException("本地文件操作客户端未正确配置：SNOWY_FILE_LOCAL_FOLDER_FOR_UNIX为空");
            }
            uploadFileFolder = localFolderForUnix;
        }
        if(!FileUtil.exist(uploadFileFolder)) {
            FileUtil.mkdir(uploadFileFolder);
        }
        return uploadFileFolder;
    }


}
