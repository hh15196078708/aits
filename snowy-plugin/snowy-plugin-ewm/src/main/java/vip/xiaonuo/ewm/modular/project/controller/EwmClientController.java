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
import vip.xiaonuo.ewm.modular.project.entity.EwmClient;
import vip.xiaonuo.ewm.modular.project.entity.SafeHardware;
import vip.xiaonuo.ewm.modular.project.param.*;
import vip.xiaonuo.ewm.modular.project.service.EwmClientService;
import vip.xiaonuo.ewm.modular.project.service.SafeHardwareService;

import java.util.List;

@Tag(name = "客户表控制器")
@ApiSupport(author = "SNOWY_CLIENT", order = 10)
@RestController
@Validated
public class EwmClientController {
    @Resource
    private EwmClientService ewmClientService;



    /**
     * 获取项目表分页
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "获取客户端表分页")
    @SaCheckPermission("/ewm/client/page")
    @GetMapping("/ewm/client/page")
    public CommonResult<Page<EwmClient>> page(EwmClientPageParam ewmClientPageParam) {
        return CommonResult.data(ewmClientService.page(ewmClientPageParam));
    }

    /**
     * 添加客户端表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "添加客户端表")
    @CommonLog("添加客户端表")
    @SaCheckPermission("/ewm/client/add")
    @PostMapping("/ewm/client/add")
    public CommonResult<String> add(@RequestBody @Valid EwmClientAddParam ewmClientAddParam) {
        ewmClientService.add(ewmClientAddParam);
        return CommonResult.ok();
    }

    @Operation(summary = "编辑客户端表")
    @CommonLog("编辑客户表")
    @SaCheckPermission("/ewm/client/edit")
    @PostMapping("/ewm/client/edit")
    public CommonResult<String> edit(@RequestBody @Valid EwmClientEditParam ewmClientEditParam) {
        ewmClientService.edit(ewmClientEditParam);
        return CommonResult.ok();
    }

    /**
     * 删除客户端表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "删除客户端表")
    @CommonLog("删除客户端表")
    @SaCheckPermission("/ewm/client/delete")
    @PostMapping("/ewm/client/delete")
    public CommonResult<String> delete(@RequestBody @Valid @NotEmpty(message = "集合不能为空")
                                       List<EwmClientIdParam> ewmClientIdParamList) {
        ewmClientService.delete(ewmClientIdParamList);
        return CommonResult.ok();
    }

    /**
     * 获取项目表详情
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    @Operation(summary = "获取客户端详情")
    @SaCheckPermission("/ewm/client/detail")
    @GetMapping("/ewm/client/detail")
    public CommonResult<EwmClient> detail(@Valid EwmClientIdParam ewmClientIdParam) {
        return CommonResult.data(ewmClientService.detail(ewmClientIdParam));
    }


}
