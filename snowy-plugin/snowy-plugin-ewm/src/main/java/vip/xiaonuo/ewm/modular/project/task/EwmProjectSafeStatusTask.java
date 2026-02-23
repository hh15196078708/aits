package vip.xiaonuo.ewm.modular.project.task;

import cn.hutool.core.date.DateUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import vip.xiaonuo.common.timer.CommonTimerTaskRunner;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectSafe;
import vip.xiaonuo.ewm.modular.project.entity.SafeHardware;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectSafeService;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@Slf4j
@Component
public class EwmProjectSafeStatusTask implements CommonTimerTaskRunner {

    @Autowired
    private EwmProjectSafeService ewmProjectSafeService;

    @Autowired
    private MongoTemplate mongoTemplate;


    @Override
    public void action(String extJson) {
        System.out.println("【终端心跳检测】开始执行");
        // 1. 计算 5 分钟前的时间点
        Date timeoutDate = DateUtil.offsetMinute(new Date(), -1);

        // 2. 获取 MySQL 中所有当前状态为 "ON" 的终端
        List<EwmProjectSafe> onlineSafes = ewmProjectSafeService.list(
                new LambdaQueryWrapper<EwmProjectSafe>().eq(EwmProjectSafe::getSafeStatus, "ON")
        );

        if (onlineSafes.isEmpty()) {
            return;
        }

        List<String> offlineSafeIds = new ArrayList<>();

        // 3. 遍历这些在线终端，去 MongoDB 中检查它们的最新心跳时间
        for (EwmProjectSafe safe : onlineSafes) {
            // 在 MongoDB 中查询该终端的最新一条记录
            Query query = new Query(Criteria.where("safe_id").is(safe.getId()));
            query.with(Sort.by(Sort.Direction.DESC, "create_time"));
            query.limit(1);

            SafeHardware latestHeartbeat = mongoTemplate.findOne(query, SafeHardware.class);

            boolean isOffline = false;

            if (latestHeartbeat != null) {
                // 3.1 存在心跳记录，判断最新心跳是否在 5 分钟前
                if (latestHeartbeat.getCreateTime().before(timeoutDate)) {
                    isOffline = true;
                }
            } else {
                // 3.2 没有任何心跳记录，判断该终端是否注册超过了 5 分钟
                if (safe.getCreateTime() != null && safe.getCreateTime().before(timeoutDate)) {
                    isOffline = true;
                }
            }

            if (isOffline) {
                offlineSafeIds.add(safe.getId());
            }
        }

        // 4. 将被判定为离线的终端，在 MySQL 中批量更新状态为 "OFF"
        if (!offlineSafeIds.isEmpty()) {
            try {
                LambdaUpdateWrapper<EwmProjectSafe> updateWrapper = new LambdaUpdateWrapper<>();
                updateWrapper.set(EwmProjectSafe::getSafeStatus, "OFF")
                        .in(EwmProjectSafe::getId, offlineSafeIds);

                boolean isUpdated = ewmProjectSafeService.update(updateWrapper);
                if (isUpdated) {
                    log.info("【终端心跳检测】检测到心跳超时，已自动将 {} 个终端状态更新为离线(OFF)", offlineSafeIds.size());
                }
            } catch (Exception e) {
                log.error("【终端心跳检测】更新终端离线状态时发生异常", e);
            }
        }
    }
}
