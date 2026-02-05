package vip.xiaonuo.filemanger.modular.files.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.hutool.json.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
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
import vip.xiaonuo.filemanger.modular.files.param.SysFilesEditParam;
import vip.xiaonuo.filemanger.modular.files.param.SysFilesPageParam;
import vip.xiaonuo.filemanger.modular.files.service.SysFilesService;

import java.io.IOException;

@Tag(name = "文件管理表控制器")
@ApiSupport(author = "Richai", order = 10)
@RestController
@Validated
public class SysFilesController {

    @Resource
    private SysFilesService sysFilesService;



    /**
     * 获取文件列表（分页 + 搜索）
     *
     * @author Snowy
     * @date 2023/10/25
     */
    @Operation(summary = "获取文件列表")
    @GetMapping("/filemanger/list")
    public CommonResult<Page<SysFiles>> list(SysFilesPageParam sysFilesPageParam) {
        return CommonResult.data(sysFilesService.page(sysFilesPageParam));
    }


    @Operation(summary = "创建文件夹")
    @SaCheckPermission("/filemanger/folder")
    @PostMapping("/filemanger/folder")
    public CommonResult<String> createFolder(@RequestBody SysFiles file) {
        file.setIsFolder(true);
        sysFilesService.createFolder(file);
        return CommonResult.ok("创建成功");
    }

    @Operation(summary = "分片检查")
    @SaCheckPermission("/filemanger/upload/checkFile")
    @GetMapping("/filemanger/upload/checkFile")
    public CommonResult<JSONObject> checkFile(@RequestParam("hash") String hash,@RequestParam("parentId") String parentId){
        return sysFilesService.checkFile(hash,parentId);
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
    public CommonResult<String> uploadChunk(@RequestParam("chunk") MultipartFile file,
                              @RequestParam("hash") String hash,
                              @RequestParam("index") Integer index) throws IOException {
        return sysFilesService.uploadChunk(file,hash,index);
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
    @Operation(summary = "文件修改")
    @SaCheckPermission("/filemanger/edit")
    @PostMapping("/filemanger/edit")
    public CommonResult<String> edit(@RequestBody SysFilesEditParam param) {
        sysFilesService.edit(param);
        return CommonResult.ok();
    }


    @Operation(summary = "文件移动")
    @SaCheckPermission("/filemanger/move")
    @PostMapping("/filemanger/move")
    public CommonResult<String> move(@RequestBody SysFilesEditParam param) {
        sysFilesService.move(param);
        return CommonResult.ok();
    }

    @Operation(summary = "文件删除")
    @SaCheckPermission("/filemanger/delete")
    @PostMapping("/filemanger/delete")
    public CommonResult<String> deleteFile(@RequestBody SysFilesEditParam param) {
        sysFilesService.deleteFile(param);
        return CommonResult.ok();
    }




}
