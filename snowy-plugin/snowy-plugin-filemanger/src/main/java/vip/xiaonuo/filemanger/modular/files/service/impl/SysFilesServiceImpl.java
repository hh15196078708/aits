package vip.xiaonuo.filemanger.modular.files.service.impl;


import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.date.DateUtil;
import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.extra.spring.SpringUtil;
import cn.hutool.json.JSONObject;
import cn.hutool.system.SystemUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import vip.xiaonuo.common.exception.CommonException;
import vip.xiaonuo.common.page.CommonPageRequest;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.dev.api.DevConfigApi;
import vip.xiaonuo.dev.modular.file.enums.DevFileEngineTypeEnum;
import vip.xiaonuo.dev.modular.file.util.DevFileLocalUtil;
import vip.xiaonuo.filemanger.modular.files.entity.SysFiles;
import vip.xiaonuo.filemanger.modular.files.mapper.SysFilesMapper;
import vip.xiaonuo.filemanger.modular.files.param.FileVO;
import vip.xiaonuo.filemanger.modular.files.param.MergeRequest;
import vip.xiaonuo.filemanger.modular.files.param.SysFilesEditParam;
import vip.xiaonuo.filemanger.modular.files.param.SysFilesPageParam;
import vip.xiaonuo.filemanger.modular.files.service.SysFilesService;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.*;
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
    private static final String SNOWY_SYS_FILE_EXE = "SNOWY_SYS_FILE_EXE";




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
        // 临时目录：uploadPath/temp/{hash}
        String tempDirPath = uploadFileFolder + File.separator + "temp" + File.separator + hash;
        File tempDir = new File(tempDirPath);
        if (!tempDir.exists()) {
            tempDir.mkdirs();
        }

        // 分片文件路径
        File chunkFile = new File(tempDir, String.valueOf(index));

        // 如果分片已存在，直接返回 skipped（前端根据此状态跳过该片）
        if (chunkFile.exists() && chunkFile.length() == chunk.getSize()) {
            return CommonResult.ok("skipped");
        }

        // 保存分片
        chunk.transferTo(chunkFile);
        return CommonResult.ok("success");
    }

    @Override
    public CommonResult<JSONObject> checkFile(String hash,String parentId) {
        JSONObject result = new JSONObject();

        // 1. 检查数据库是否已存在该 MD5 且状态正常的文件 (秒传逻辑)
        // 假设你的 SysFiles 实体类中有 fileMd5 字段
        SysFiles existingFile = this.getOne(new LambdaQueryWrapper<SysFiles>()
                .eq(SysFiles::getFileMd5, hash)
                .eq(SysFiles::getParentId,parentId)
                .last("LIMIT 1"));

        if (existingFile != null) {
            result.set("needUpload", false); // 告诉前端不需要上传，直接调秒传成功逻辑
            return CommonResult.data(result);
        }

        // 2. 检查临时目录，返回已上传的分片索引列表 (断点续传逻辑)
        result.set("needUpload", true);
        String tempDirPath = getUploadPath() + File.separator + "temp" + File.separator + hash;
        File tempDir = new File(tempDirPath);

        List<Integer> uploadedChunks = new ArrayList<>();
        if (tempDir.exists() && tempDir.isDirectory()) {
            File[] files = tempDir.listFiles();
            if (files != null) {
                for (File f : files) {
                    if (f.isFile()) {
                        uploadedChunks.add(Integer.parseInt(f.getName()));
                    }
                }
            }
        }
        result.set("uploadedChunks", uploadedChunks); // 返回 [0, 1, 5] 等已上传的编号
        return CommonResult.data(result);
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
        String originalFileName = mergeRequest.getFileName();
        String extName = "";
        if (originalFileName.contains(".")) {
            extName = originalFileName.substring(originalFileName.lastIndexOf(".") + 1).toLowerCase();
        }
        String suffix = fileName.contains(".") ? fileName.substring(fileName.lastIndexOf(".")) : "";
        String realFileName = UUID.randomUUID().toString() + suffix; // 避免重名
        Path targetPath = Paths.get(uploadPath+"/"+dateFolderPath, realFileName);
        // 确保目标文件的父目录存在
        Path parentDir = targetPath.getParent();
        if (parentDir != null && !Files.exists(parentDir)) {
            Files.createDirectories(parentDir);
        }
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
        //判断当前文件格式是否合法
        checkFileExtension(originalFileName);
// 6. 保存到数据库
        SysFiles sysFile = new SysFiles();
        sysFile.setName(fileName);
        sysFile.setParentId("null".equals(parentId) ? null : parentId);
        sysFile.setIsFolder(false);
        sysFile.setFileSize(Files.size(targetPath));
        sysFile.setFilePath(targetPath.toString());
        sysFile.setContentType(Files.probeContentType(targetPath));
        sysFile.setFileMd5(hash);
        sysFile.setFileType(extName);
        this.save(sysFile);

        FileVO fileVO = FileVO.fromEntity(sysFile);
        return CommonResult.data(fileVO);
    }

    @Override
    public Page<SysFiles> page(SysFilesPageParam sysFilesPageParam) {
        LambdaQueryWrapper<SysFiles> queryWrapper = new LambdaQueryWrapper<>();

        // 1. 处理搜索 (如果存在搜索关键词，则忽略 parentId 进行全局搜索，或者你也可以限制在当前目录下搜索)
        // 这里的逻辑是：如果有 searchKeyword，进行模糊查询；如果没有，则严格按照 parentId 查询
        if (ObjectUtil.isNotEmpty(sysFilesPageParam.getSearchKeyword())) {
            queryWrapper.like(SysFiles::getName, sysFilesPageParam.getSearchKeyword());
            // 如果希望搜索也限制在当前目录下，解开下面这行注释
            // if (ObjectUtil.isNotEmpty(sysFilesPageParam.getParentId())) { queryWrapper.eq(SysFiles::getParentId, sysFilesPageParam.getParentId()); }
        }
        // 2. 处理层级
        if (ObjectUtil.isEmpty(sysFilesPageParam.getParentId())) {
            sysFilesPageParam.setParentId("0");
        }
        if(ObjectUtil.isNotEmpty(sysFilesPageParam.getIsFolder())){
            queryWrapper.eq(SysFiles::getIsFolder, sysFilesPageParam.getIsFolder());
        }
        queryWrapper.eq(SysFiles::getParentId, sysFilesPageParam.getParentId());

        // 3. 排序：文件夹在前，文件在后；然后按 sortCode 升序，最后按 updateTime 倒序
        // 注意：数据库要有 is_folder 和 sort_code 字段，如果没有请根据实际 Entity 修改
        queryWrapper.orderByDesc(SysFiles::getIsFolder);
        // queryWrapper.orderByAsc(SysFiles::getSortCode); // 如果你的实体没有 sortCode，请注释这行
        queryWrapper.orderByDesc(SysFiles::getCreateTime);
        return this.page(CommonPageRequest.defaultPage(), queryWrapper);
//        return this.page(new Page<>(sysFilesPageParam.getCurrent(), sysFilesPageParam.getSize()), queryWrapper);
    }

    @Override
    public void edit(SysFilesEditParam param) {
        SysFiles isFiles = baseMapper.selectById(param.getId());
        //检查是否为空
        if (isFiles == null) {
            throw new RuntimeException("文件不存在");
        }
        Long count = baseMapper.selectCount(
                new QueryWrapper<SysFiles>()
                        .eq("parent_id", param.getParentId())
                        .eq("name", param.getName())
                        .eq("DELETE_FLAG", "NOT_DELETE")
        );
        if (count > 0) {
            throw new RuntimeException("当前目录下已存在同名名称");
        }
        SysFiles sysFiles = new SysFiles();
        BeanUtil.copyProperties(param, sysFiles);
        this.updateById(sysFiles);
    }

    @Override
    public void move(SysFilesEditParam param) {
        // 1. 获取数据库中的原始记录
        SysFiles oldFile = this.getById(param.getId());
        if (oldFile == null) {
            throw new CommonException("文件记录不存在");
        }

        String newParentId = param.getParentId();
        // 校验 2：不能移动到自己及自己的子目录下
        if (oldFile.getIsFolder()) {
            if (newParentId.equals(oldFile.getId())) {
                throw new CommonException("无法将文件夹移动到自身内部");
            }

            // 递归检查目标 ID 是否是当前文件夹的子节点
            if (isChildNode(oldFile.getId(), newParentId)) {
                throw new CommonException("无法将文件夹移动到其子文件夹下");
            }
        }

        // 2. 核心校验：判断是否正在移动根目录下的文件夹
        // 逻辑：如果原始记录是一个文件夹，且它的 parentId 是 '0'（根目录）
        // 并且前端传来的新 parentId 与原始的不一致（说明在尝试移动位置）
//        if (oldFile.getIsFolder() && "0".equals(oldFile.getParentId())) {
//            if (StrUtil.isNotBlank(param.getParentId()) &&
//                    !"0".equals(param.getParentId())) {
//                throw new CommonException("根目录下的文件夹不允许移动");
//            }
//        }

        // 3. 执行更新逻辑
        SysFiles sysFiles = new SysFiles();
        BeanUtil.copyProperties(param, sysFiles);

        // 如果 parentId 是 "0" 或 "null" 字符串，统一转为数据库标准的 "0" 或 null
        if("null".equals(sysFiles.getParentId()) || StrUtil.isBlank(sysFiles.getParentId())) {
            sysFiles.setParentId("0");
        }

        this.updateById(sysFiles);
    }
    @Transactional(rollbackFor = Exception.class)
    @Override
    public void deleteFile(SysFilesEditParam param) {
        SysFiles sysFile = this.getById(param.getId());
        if (sysFile == null) {
            throw new RuntimeException("文件不存在");
        }
        List<String> idsToDelete = new ArrayList<>();
        idsToDelete.add(param.getId());

        // 如果是文件夹，递归获取所有下级 ID
        if (sysFile.getIsFolder()) {
            findAllChildIds(param.getId(), idsToDelete);
        }

        // 1. 获取这批 ID 中所有的“文件”（非文件夹），用于删除物理磁盘文件
        List<SysFiles> filesInDb = this.list(new LambdaQueryWrapper<SysFiles>()
                .in(SysFiles::getId, idsToDelete)
                .eq(SysFiles::getIsFolder, false));

        for (SysFiles file : filesInDb) {
            if (StrUtil.isNotBlank(file.getFilePath())) {
                // 使用 Hutool 的 FileUtil 删除磁盘文件
                FileUtil.del(file.getFilePath());
            }
        }

        // 2. 批量从数据库删除记录（包括文件夹本身和下级所有内容）
        this.removeByIds(idsToDelete);
    }

    /**
     * 递归查找所有子节点 ID
     */
    private void findAllChildIds(String parentId, List<String> ids) {
        List<SysFiles> children = this.list(new LambdaQueryWrapper<SysFiles>()
                .eq(SysFiles::getParentId, parentId));

        for (SysFiles child : children) {
            ids.add(child.getId());
            if (child.getIsFolder()) {
                // 如果子项还是文件夹，继续递归
                findAllChildIds(child.getId(), ids);
            }
        }
    }

    /**
     * 递归判断 targetId 是否是 originId 的子节点
     */
    private boolean isChildNode(String originId, String targetId) {
        // 查询所有父级为 originId 的子项
        List<SysFiles> children = this.list(new LambdaQueryWrapper<SysFiles>()
                .eq(SysFiles::getParentId, originId)
                .eq(SysFiles::getIsFolder, true));

        for (SysFiles child : children) {
            if (child.getId().equals(targetId)) {
                return true;
            }
            // 继续递归向下查找
            if (isChildNode(child.getId(), targetId)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 校验文件格式是否合法
     * @param fileName 文件名（从前端 MergeRequest 或 MultipartFile 中获取）
     */
    private static void checkFileExtension(String fileName) {

        DevConfigApi devConfigApi = SpringUtil.getBean(DevConfigApi.class);

        String fileExe = devConfigApi.getValueByKey(SNOWY_SYS_FILE_EXE);
        //字符串按照@切割为数组
        String[] fileExes = fileExe.split("@");

        if (StrUtil.isBlank(fileName)) {
            throw new CommonException("文件名不能为空");
        }

        // 获取扩展名并转为小写 (Hutool方法：example.JPG -> jpg)
        String extName = FileUtil.extName(fileName).toLowerCase();

        // 校验是否存在于白名单中
        if (!Arrays.asList(fileExes).contains(extName)) {
            throw new CommonException("不支持的文件格式：" + extName);
        }
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
