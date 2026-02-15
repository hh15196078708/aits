package vip.xiaonuo.ewm.modular.project.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import io.lettuce.core.dynamic.annotation.Param;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectList;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafe;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafeList;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectPageParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafePageParam;

/**
 * 网络安全的客户端Mapper接口
 *
 * @author Richai
 * @date  2026/02/09 15:57
 **/
public interface EwmProjectSafeMapper extends BaseMapper<EwmProjectSafe> {
    IPage<EwmProjectSafeList> selectEwmProjectSafeList(IPage<EwmProjectSafeList> page, @Param("ewmProjectSafePageParam") EwmProjectSafePageParam ewmProjectSafePageParam);
}
