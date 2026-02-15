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
     * 获取网络安全的客户端分页
     *
     * @author Richai
     * @date 2026/02/15 23:15
     */
    Page<EwmProjectSafeList> page(EwmProjectSafePageParam ewmProjectSafePageParam);
}
