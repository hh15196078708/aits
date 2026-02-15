package vip.xiaonuo.ewm.modular.project.service;

import cn.hutool.core.util.ObjectUtil;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;
import vip.xiaonuo.ewm.modular.project.entity.SafeHardware;
import vip.xiaonuo.ewm.modular.project.repository.SafeHardwareRepository;

import java.util.Calendar;
import java.util.Date;
import java.util.List;

@Service
public class SafeHardwareService {

    @Autowired
    private SafeHardwareRepository safeHardwareRepository;

    @Resource
    private MongoTemplate mongoTemplate;

    public SafeHardware save(SafeHardware safeHardware) {
        return safeHardwareRepository.save(safeHardware);
    }

    public List<SafeHardware> monitor(String safeId, String timeRange) {
        if (ObjectUtil.isEmpty(safeId)) {
            return List.of();
        }

        // 计算开始时间
        Date now = new Date();
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(now);

        if ("24h".equals(timeRange)) {
            calendar.add(Calendar.HOUR_OF_DAY, -24);
        } else if ("7d".equals(timeRange)) {
            calendar.add(Calendar.DAY_OF_YEAR, -7);
        } else {
            // 默认1小时
            calendar.add(Calendar.HOUR_OF_DAY, -1);
        }
        Date startTime = calendar.getTime();

        // 构建查询条件
        Query query = new Query();
        query.addCriteria(Criteria.where("safe_id").is(safeId).and("create_time").gte(startTime));

        // 按时间升序排列，方便前端直接绘图
        query.with(Sort.by(Sort.Direction.ASC, "create_time"));

        return mongoTemplate.find(query, SafeHardware.class);
    }
}
