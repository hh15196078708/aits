package vip.xiaonuo.ewm.modular.project.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.constraints.NotEmpty;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import vip.xiaonuo.common.annotation.CommonLog;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.*;
import vip.xiaonuo.ewm.modular.project.param.*;
import vip.xiaonuo.ewm.modular.project.service.AttackPortScanService;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectSafeService;
import vip.xiaonuo.ewm.modular.project.service.EwmSafeConfigService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import vip.xiaonuo.ewm.modular.project.service.SafeHardwareService;
import vip.xiaonuo.ewm.modular.project.service.SafeWebSocketService;
import vip.xiaonuo.ewm.modular.project.service.WebAttackService;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
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

    @Resource
    private WebAttackService webAttackService;

    @Resource
    private SafeWebSocketService safeWebSocketService;

    @Resource
    private EwmSafeConfigService ewmSafeConfigService;

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

    @Operation(summary = "web日志上传")
    @PostMapping("/init/attack/web")
    public CommonResult<String> webAttactk(@RequestBody WebAttackReportRequest webAttackReportRequest){
        return webAttackService.save(webAttackReportRequest);
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

    /**
     * 获取web攻击日志分页 (来自 MongoDB)
     */
    @Operation(summary = "获取web攻击日志记录分页")
    @GetMapping("/webattack/page")
    public CommonResult<Page<WebAttack>> webAttackpage(WebAttackPageParam webAttackPageParam) {
        Page<WebAttack> page = webAttackService.page(webAttackPageParam);
        return CommonResult.data(page);
    }

    // ----------------------------------------------------------------
    // 终端安全配置接口
    // ----------------------------------------------------------------

    @Operation(summary = "获取终端安全配置")
    @GetMapping("/projectsafe/config/detail")
    public CommonResult<EwmSafeConfig> getConfig(@NotEmpty(message = "终端ID不能为空") String safeId) {
        EwmSafeConfig config = ewmSafeConfigService.getConfigBySafeId(safeId);
        return CommonResult.data(config);
    }

    @Operation(summary = "保存终端安全配置")
    @CommonLog("保存终端安全配置")
    @PostMapping("/projectsafe/config/save")
    public CommonResult<String> saveConfig(@RequestBody @Validated EwmSafeConfigParam param) {
        ewmSafeConfigService.saveConfig(param);
        return CommonResult.ok("配置保存成功");
    }

    @Operation(summary = "下载终端安全配置JSON")
    @GetMapping("/projectsafe/config/download")
    public void downloadConfig(@NotEmpty(message = "终端ID不能为空") String safeId, HttpServletResponse response) throws IOException {
        String json = ewmSafeConfigService.generateConfigJson(safeId);
        response.setContentType("application/json;charset=UTF-8");
        response.setHeader("Content-Disposition",
                "attachment;filename=" + URLEncoder.encode("client_config.json", StandardCharsets.UTF_8));
        response.getWriter().write(json);
        response.getWriter().flush();
    }

    // ----------------------------------------------------------------
    // WSS 指令下发接口
    // ----------------------------------------------------------------

    @Operation(summary = "下发自动拉黑开关指令")
    @CommonLog("下发自动拉黑开关指令")
    @PostMapping("/ws/command/autoblock")
    public CommonResult<String> wsCmdAutoBlock(@RequestBody @Validated WsAutoBlockParam param) {
        return safeWebSocketService.sendAutoBlock(param);
    }

    @Operation(summary = "下发封禁IP指令")
    @CommonLog("下发封禁IP指令")
    @PostMapping("/ws/command/blockip")
    public CommonResult<String> wsCmdBlockIp(@RequestBody @Validated WsBlockIpParam param) {
        return safeWebSocketService.sendBlockIp(param);
    }

    @Operation(summary = "下发IP白名单更新指令")
    @CommonLog("下发IP白名单更新指令")
    @PostMapping("/ws/command/whitelist")
    public CommonResult<String> wsCmdWhitelist(@RequestBody @Validated WsWhitelistParam param) {
        return safeWebSocketService.sendWhitelist(param);
    }

    @Operation(summary = "下发关机指令")
    @CommonLog("下发关机指令")
    @PostMapping("/ws/command/shutdown")
    public CommonResult<String> wsCmdShutdown(@RequestBody @Validated WsClientIdParam param) {
        return safeWebSocketService.sendShutdown(param);
    }
}
