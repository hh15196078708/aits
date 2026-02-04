package vip.xiaonuo.filemanger.modular.files.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.github.xiaoymin.knife4j.annotations.ApiSupport;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.filemanger.modular.files.entity.SysFiles;
import vip.xiaonuo.filemanger.modular.files.param.FileVO;
import vip.xiaonuo.filemanger.modular.files.param.MergeRequest;
import vip.xiaonuo.filemanger.modular.files.service.SysFilesService;

import java.io.IOException;

@Tag(name = "文件管理表控制器")
@ApiSupport(author = "Richai", order = 10)
@RestController
@Validated
public class SysFilesController {

    @Resource
    private SysFilesService sysFilesService;


    @Operation(summary = "创建文件夹")
    @SaCheckPermission("/filemanger/folder")
    @PostMapping("/filemanger/folder")
    public CommonResult<String> createFolder(@RequestBody SysFiles file) {
        file.setIsFolder(true);
        sysFilesService.createFolder(file);
        return CommonResult.ok("创建成功");
    }

    /**
     * 3.1 分片上传接口
     * 前端遍历分片，依次调用此接口
     * @param chunk 当前分片文件
     * @param hash  文件唯一标识 (MD5)
     * @param index 当前分片序号 (0, 1, 2...)
     */
    @Operation(summary = "分片上传")
    @SaCheckPermission("/filemanger/upload/chunk")
    @PostMapping("/filemanger/upload/chunk")
    public CommonResult<String> uploadChunk(@RequestParam("chunk") MultipartFile chunk,
                              @RequestParam("hash") String hash,
                              @RequestParam("index") Integer index) throws IOException {
        return sysFilesService.uploadChunk(chunk,hash,index);
        // 临时目录: uploadPath/temp/{hash}

    }

    /**
     * 3.2 合并分片接口
     * 前端所有分片上传成功后，调用此接口通知合并
     */
    @Operation(summary = "合并分片")
    @SaCheckPermission("/filemanger/upload/merge")
    @PostMapping("/filemanger/upload/merge")
    public CommonResult<FileVO> mergeChunks(@RequestBody MergeRequest request) throws IOException {
        return sysFilesService.mergeChunks(request);
    }




}
