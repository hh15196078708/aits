package vip.xiaonuo.ewm.modular.project.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.github.xiaoymin.knife4j.annotations.ApiSupport;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import vip.xiaonuo.common.annotation.CommonLog;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.EwmProject;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectList;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectEditParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectIdParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectPageParam;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectService;

import java.util.List;

/**
 * 项目表控制器
 *
 * @author Richai
 * @date  2025/12/24 14:44
 */
@Tag(name = "项目表控制器")
@ApiSupport(author = "SNOWY_TEAM", order = 9)
@RestController
@Validated
public class EwmProjectController {

    @Resource
    private EwmProjectService ewmProjectService;

    /**
     * 获取项目表分页
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "获取项目表分页")
    @SaCheckPermission("/ewm/project/page")
    @GetMapping("/ewm/project/page")
    public CommonResult<Page<EwmProjectList>> page(EwmProjectPageParam ewmProjectPageParam) {
        return CommonResult.data(ewmProjectService.page(ewmProjectPageParam));
    }

    /**
     * 添加项目表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "添加项目表")
    @CommonLog("添加项目表")
    @SaCheckPermission("/ewm/project/add")
    @PostMapping("/ewm/project/add")
    public CommonResult<String> add(@RequestBody @Valid EwmProjectAddParam ewmProjectAddParam) {
        ewmProjectService.add(ewmProjectAddParam);
        return CommonResult.ok();
    }

    /**
     * 编辑项目表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "编辑项目表")
    @CommonLog("编辑项目表")
    @SaCheckPermission("/ewm/project/edit")
    @PostMapping("/ewm/project/edit")
    public CommonResult<String> edit(@RequestBody @Valid EwmProjectEditParam ewmProjectEditParam) {
        ewmProjectService.edit(ewmProjectEditParam);
        return CommonResult.ok();
    }

    /**
     * 删除项目表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "删除项目表")
    @CommonLog("删除项目表")
    @SaCheckPermission("/ewm/project/delete")
    @PostMapping("/ewm/project/delete")
    public CommonResult<String> delete(@RequestBody @Valid @NotEmpty(message = "集合不能为空")
                                       List<EwmProjectIdParam> ewmProjectIdParamList) {
        ewmProjectService.delete(ewmProjectIdParamList);
        return CommonResult.ok();
    }

    /**
     * 获取项目表详情
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "获取项目表详情")
    @SaCheckPermission("/ewm/project/detail")
    @GetMapping("/ewm/project/detail")
    public CommonResult<EwmProject> detail(@Valid EwmProjectIdParam ewmProjectIdParam) {
        return CommonResult.data(ewmProjectService.detail(ewmProjectIdParam));
    }



}
