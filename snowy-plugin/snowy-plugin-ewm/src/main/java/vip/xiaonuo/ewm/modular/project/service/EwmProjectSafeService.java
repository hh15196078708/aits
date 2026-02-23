package vip.xiaonuo.ewm.modular.project.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectList;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafe;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafeList;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeCheckParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafePageParam;

public interface EwmProjectSafeService extends IService<EwmProjectSafe> {

    CommonResult<EwmProjectSafe> initReg(EwmProjectSafeAddParam ewmProjectSafeAddParam);

    /**
     * 校验终端授权
     *
     * @param ewmProjectSafeCheckParam 校验参数
     * @return 是否校验通过
     */
    CommonResult<String> checkAuth(EwmProjectSafeCheckParam ewmProjectSafeCheckParam);

    /**
     * WSS 心跳专用：校验终端授权并更新硬件数据
     *
     * 与 checkAuth 逻辑相同，但返回 boolean 而非 CommonResult，
     * 供 WebSocketServer 直接判断授权是否有效。
     *
     * @param param 心跳参数（id, projectId, safeCode, safeSecret, 硬件数据）
     * @return true=授权有效，false=校验失败或授权已过期
     */
    boolean checkWsHeartbeat(EwmProjectSafeCheckParam param);

    /**
     * 更新终端在线状态（WSS 连接断开时调用，将状态置为 OFF）
     *
     * @param safeId 终端 ID（ewm_project_safe.id）
     * @param status "ON" 或 "OFF"
     */
    void updateOnlineStatus(String safeId, String status);

    /**
     * 获取网络安全的客户端分页
     *
     * @author Richai
     * @date 2026/02/15 23:15
     */
    Page<EwmProjectSafeList> page(EwmProjectSafePageParam ewmProjectSafePageParam);
}
