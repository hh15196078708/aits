package vip.xiaonuo.ewm.modular.project.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import jakarta.validation.constraints.NotEmpty;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import vip.xiaonuo.common.annotation.CommonLog;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.*;
import vip.xiaonuo.ewm.modular.project.param.AttackPortScanPageParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeCheckParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafePageParam;
import vip.xiaonuo.ewm.modular.project.service.AttackPortScanService;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectSafeService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import vip.xiaonuo.ewm.modular.project.service.SafeHardwareService;

import java.util.List;

/**
 * 网络安全的客户端控制器
 *
 * @author Richai
 * @date  2026/02/09 15:57
 */
@Tag(name = "网络安全的客户端控制器")
@RestController
@Validated
@RequestMapping("/safe")
public class EwmProjectSafeController {

    @Resource
    private EwmProjectSafeService ewmProjectSafeService;

    @Resource
    private SafeHardwareService safeHardwareService;

    @Resource
    private AttackPortScanService attackPortScanService;

    /**
     * 获取网络安全的客户端分页
     *
     * @author Richai
     * @date  2026/02/15 23:15
     */
    @Operation(summary = "获取网络安全的客户端分页")
    @GetMapping("/projectsafe/page")
    public CommonResult<Page<EwmProjectSafeList>> page(EwmProjectSafePageParam ewmProjectSafePageParam) {
        Page<EwmProjectSafeList> page = ewmProjectSafeService.page(ewmProjectSafePageParam);
        return CommonResult.data(page);
    }

    @Operation(summary = "添加网络安全的客户端")
    @CommonLog("添加网络安全的客户端")
    @PostMapping("/init/add")
    public CommonResult<EwmProjectSafe> initReg(@RequestBody EwmProjectSafeAddParam ewmProjectSafeAddParam) {
        return ewmProjectSafeService.initReg(ewmProjectSafeAddParam);
    }

    @Operation(summary = "校验终端")
    @CommonLog("校验终端")
    @PostMapping("/init/check")
    public CommonResult<String> check(@RequestBody EwmProjectSafeCheckParam ewmProjectSafeCheckParam) {
        return ewmProjectSafeService.checkAuth(ewmProjectSafeCheckParam);
    }

    /**
     * 获取硬件监控数据
     *
     * @author Snowy
     * @date 2023/10/25 10:00
     */
    @Operation(summary = "获取监控数据")
    @GetMapping("/projectsafe/monitor")
    public CommonResult<List<SafeHardware>> monitor(@NotEmpty(message = "设备ID不能为空") String safeId, String timeRange) {
        return CommonResult.data(safeHardwareService.monitor(safeId, timeRange));
    }

    @Operation(summary = "端口扫描日志上传")
    @PostMapping("/init/attack/portscan")
    public CommonResult<String> portScan(@RequestBody PortScanReportRequest attackPortScan){
        return attackPortScanService.save(attackPortScan);
    }



    /**
     * 获取端口扫描记录分页 (来自 MongoDB)
     */
    @Operation(summary = "获取端口扫描记录分页")
    @GetMapping("/portscan/page")
    public CommonResult<Page<AttackPortScan>> page(AttackPortScanPageParam attackPortScanPageParam) {
        Page<AttackPortScan> page = attackPortScanService.page(attackPortScanPageParam);
        return CommonResult.data(page);
    }
}
