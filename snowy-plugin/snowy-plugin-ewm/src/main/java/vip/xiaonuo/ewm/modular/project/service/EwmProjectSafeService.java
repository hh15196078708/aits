package vip.xiaonuo.ewm.modular.project.service;

import com.baomidou.mybatisplus.extension.service.IService;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafe;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeCheckParam;

public interface EwmProjectSafeService extends IService<EwmProjectSafe> {

    CommonResult<EwmProjectSafe> initReg(EwmProjectSafeAddParam ewmProjectSafeAddParam);

    /**
     * 校验终端授权
     *
     * @param ewmProjectSafeCheckParam 校验参数
     * @return 是否校验通过
     */
    CommonResult<String> checkAuth(EwmProjectSafeCheckParam ewmProjectSafeCheckParam);

}
