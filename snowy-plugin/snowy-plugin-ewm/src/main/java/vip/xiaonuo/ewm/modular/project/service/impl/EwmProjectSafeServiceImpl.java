package vip.xiaonuo.ewm.modular.project.service.impl;

import cn.hutool.core.date.DateUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.RandomUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.springframework.stereotype.Service;
import vip.xiaonuo.common.exception.CommonException;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafe;
import vip.xiaonuo.ewm.modular.project.mapper.EwmProjectSafeMapper;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeCheckParam;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectSafeService;

import java.util.Date;

/**
 * 网络安全的客户端Service接口实现类
 *
 * @author Richai
 * @date 2026/02/09 15:57
 **/
@Service
public class EwmProjectSafeServiceImpl extends ServiceImpl<EwmProjectSafeMapper, EwmProjectSafe> implements EwmProjectSafeService {

    @Override
    public CommonResult<EwmProjectSafe> initReg(EwmProjectSafeAddParam ewmProjectSafeAddParam) {
        LambdaQueryWrapper<EwmProjectSafe> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(EwmProjectSafe::getProjectId, ewmProjectSafeAddParam.getProjectId());
        queryWrapper.eq(EwmProjectSafe::getSafeCode, ewmProjectSafeAddParam.getSafeCode());
        EwmProjectSafe safe = this.getOne(queryWrapper);
        if (ObjectUtil.isNotEmpty(safe)) {
            // 2. 如果存在，更新基本信息 (IP, OS, Name, Status)
            safe.setSafeName(ewmProjectSafeAddParam.getSafeName());
            safe.setSafeOs(ewmProjectSafeAddParam.getSafeOs());
            safe.setSafeIp(ewmProjectSafeAddParam.getSafeIp());
            safe.setSafeStatus("ON"); // 注册即视为在线
            this.updateById(safe);
            return CommonResult.data(safe);
        } else {
            // 3. 如果不存在，创建新记录
            EwmProjectSafe newSafe = new EwmProjectSafe();
            newSafe.setProjectId(ewmProjectSafeAddParam.getProjectId());
            newSafe.setSafeCode(ewmProjectSafeAddParam.getSafeCode());
            newSafe.setSafeName(ewmProjectSafeAddParam.getSafeName());
            newSafe.setSafeOs(ewmProjectSafeAddParam.getSafeOs());
            newSafe.setSafeIp(ewmProjectSafeAddParam.getSafeIp());

            // 生成随机密钥
            newSafe.setSafeSecret(RandomUtil.randomString(32));
            newSafe.setSafeStatus("ON");
            // 默认授权时间 (可选，根据业务需求，这里默认给一个月或置空由后台审核)
            newSafe.setSafeStartTime(new Date());
            newSafe.setSafeEndTime(DateUtil.offsetMonth(new Date(), 1));
            this.save(newSafe);
            return CommonResult.data(newSafe);
        }
    }

    @Override
    public CommonResult<String> checkAuth(EwmProjectSafeCheckParam ewmProjectSafeCheckParam) {
        // 1. 根据ID查询
        EwmProjectSafe safe = this.getById(ewmProjectSafeCheckParam.getId());
        if (ObjectUtil.isEmpty(safe)) {
            return CommonResult.error("终端未注册");
        }

        // 2. 校验所属项目
        if (!safe.getProjectId().equals(ewmProjectSafeCheckParam.getProjectId())) {
            return CommonResult.error("终端项目归属异常");
        }

        // 3. 校验机器码 (防止伪造ID)
        if (!safe.getSafeCode().equals(ewmProjectSafeCheckParam.getSafeCode())) {
            return CommonResult.error("终端机器码异常");
        }

        // 4. 校验密钥
        if (!safe.getSafeSecret().equals(ewmProjectSafeCheckParam.getSafeSecret())) {
            return CommonResult.error("终端密钥异常");
        }

        // 5. 校验授权时间 (如果设置了时间限制)
        Date now = new Date();
        if (ObjectUtil.isNotEmpty(safe.getSafeStartTime()) && now.before(safe.getSafeStartTime())) {
            return CommonResult.error("终端授权未生效");
        }
        if (ObjectUtil.isNotEmpty(safe.getSafeEndTime()) && now.after(safe.getSafeEndTime())) {
            return CommonResult.error("终端授权已过期");
        }

        // 6. 更新在线状态 (可选：这里可以做心跳逻辑，刷新最后活跃时间等)
        safe.setSafeStatus("ON");
        safe.setUpdateTime(new Date());
        this.updateById(safe);
        return CommonResult.ok("终端授权有效");
    }
}
