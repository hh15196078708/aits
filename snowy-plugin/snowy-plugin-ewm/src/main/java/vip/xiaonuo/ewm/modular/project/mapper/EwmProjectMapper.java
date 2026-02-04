package vip.xiaonuo.ewm.modular.project.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import io.lettuce.core.dynamic.annotation.Param;
import vip.xiaonuo.ewm.modular.project.entity.EwmProject;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectList;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectPageParam;

import java.util.List;

/**
 * 项目表Mapper接口
 *
 * @author Richai
 * @date  2025/12/24 14:44
 **/
public interface EwmProjectMapper extends BaseMapper<EwmProject> {

    IPage<EwmProjectList> selectEwmProjectAndOrgList(IPage<EwmProjectList> page, @Param("ewmProjectPageParam") EwmProjectPageParam ewmProjectPageParam);
}
