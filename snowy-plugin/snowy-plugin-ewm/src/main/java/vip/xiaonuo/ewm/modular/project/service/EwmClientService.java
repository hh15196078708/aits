package vip.xiaonuo.ewm.modular.project.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import vip.xiaonuo.ewm.modular.project.entity.EwmClient;
import vip.xiaonuo.ewm.modular.project.param.EwmClientAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmClientEditParam;
import vip.xiaonuo.ewm.modular.project.param.EwmClientIdParam;
import vip.xiaonuo.ewm.modular.project.param.EwmClientPageParam;

import java.util.List;

/**
 * 客户管理Service接口
 *
 * @author Snowy
 * @date 2024-05-20
 */
public interface EwmClientService extends IService<EwmClient> {

    /**
     * 获取客户分页
     */
    Page<EwmClient> page(EwmClientPageParam ewmClientPageParam);

    /**
     * 添加客户
     */
    void add(EwmClientAddParam ewmClientAddParam);

    /**
     * 编辑客户
     */
    void edit(EwmClientEditParam ewmClientEditParam);

    /**
     * 删除客户
     */
    void delete(List<EwmClientIdParam> ewmClientIdParamList);

    /**
     * 获取客户详情
     */
    EwmClient detail(EwmClientIdParam ewmClientIdParam);
}
