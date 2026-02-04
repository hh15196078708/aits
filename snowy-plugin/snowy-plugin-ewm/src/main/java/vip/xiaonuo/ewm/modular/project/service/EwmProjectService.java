package vip.xiaonuo.ewm.modular.project.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import vip.xiaonuo.ewm.modular.project.entity.EwmProject;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectList;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectEditParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectIdParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectPageParam;

import java.util.List;

public interface EwmProjectService extends IService<EwmProject> {

    /**
     * 获取项目表分页
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    Page<EwmProjectList> page(EwmProjectPageParam ewmProjectPageParam);

    /**
     * 添加项目表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    void add(EwmProjectAddParam ewmProjectAddParam);

    /**
     * 编辑项目表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    void edit(EwmProjectEditParam ewmProjectEditParam);

    /**
     * 删除项目表
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    void delete(List<EwmProjectIdParam> ewmProjectIdParamList);

    /**
     * 获取项目表详情
     *
     * @author Richai
     * @date  2025/12/30 14:28
     */
    EwmProject detail(EwmProjectIdParam ewmProjectIdParam);

    /**
     * 获取项目表详情
     *
     * @author Richai
     * @date  2025/12/30 14:28
     **/
    EwmProject queryEntity(String id);
}
