package vip.xiaonuo.ewm.modular.project.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.springframework.stereotype.Service;
import vip.xiaonuo.common.enums.CommonSortOrderEnum;
import vip.xiaonuo.common.exception.CommonException;
import vip.xiaonuo.common.page.CommonPageRequest;
import vip.xiaonuo.ewm.modular.project.entity.EwmClient;
import vip.xiaonuo.ewm.modular.project.mapper.EwmClientMapper;
import vip.xiaonuo.ewm.modular.project.param.EwmClientAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmClientEditParam;
import vip.xiaonuo.ewm.modular.project.param.EwmClientIdParam;
import vip.xiaonuo.ewm.modular.project.param.EwmClientPageParam;
import vip.xiaonuo.ewm.modular.project.service.EwmClientService;

import java.util.List;

/**
 * 客户管理Service接口实现类
 *
 * @author Snowy
 * @date 2024-05-20
 */
@Service
public class EwmClientServiceImpl  extends ServiceImpl<EwmClientMapper, EwmClient> implements EwmClientService {

    @Override
    public Page<EwmClient> page(EwmClientPageParam ewmClientPageParam) {
        QueryWrapper<EwmClient> queryWrapper = new QueryWrapper<>();
        if(ObjectUtil.isNotEmpty(ewmClientPageParam.getName())) {
            queryWrapper.lambda().like(EwmClient::getName, ewmClientPageParam.getName());
        }
        // 支持按经办人搜索
        if(ObjectUtil.isNotEmpty(ewmClientPageParam.getAgent())) {
            queryWrapper.lambda().like(EwmClient::getAgent, ewmClientPageParam.getAgent());
        }
        if(ObjectUtil.isAllNotEmpty(ewmClientPageParam.getSortField(), ewmClientPageParam.getSortOrder())) {
            CommonSortOrderEnum.validate(ewmClientPageParam.getSortOrder());
            queryWrapper.orderBy(true, ewmClientPageParam.getSortOrder().equals(CommonSortOrderEnum.ASC.getValue()),
                    StrUtil.toUnderlineCase(ewmClientPageParam.getSortField()));
        } else {
            queryWrapper.lambda().orderByAsc(EwmClient::getSortCode);
        }
        return this.page(CommonPageRequest.defaultPage(), queryWrapper);
    }

    @Override
    public void add(EwmClientAddParam ewmClientAddParam) {
        EwmClient ewmClient = BeanUtil.toBean(ewmClientAddParam, EwmClient.class);
        this.save(ewmClient);
    }

    @Override
    public void edit(EwmClientEditParam ewmClientEditParam) {
        EwmClient ewmClient = this.queryEwmClient(ewmClientEditParam.getId());
        BeanUtil.copyProperties(ewmClientEditParam, ewmClient);
        this.updateById(ewmClient);
    }

    @Override
    public void delete(List<EwmClientIdParam> ewmClientIdParamList) {
        this.removeByIds(CollUtil.getFieldValues(ewmClientIdParamList, "id", String.class));
    }

    @Override
    public EwmClient detail(EwmClientIdParam ewmClientIdParam) {
        return this.queryEwmClient(ewmClientIdParam.getId());
    }

    private EwmClient queryEwmClient(String id) {
        EwmClient ewmClient = this.getById(id);
        if(ObjectUtil.isEmpty(ewmClient)) {
            throw new CommonException("客户不存在，id值为：{}", id);
        }
        return ewmClient;
    }
}
