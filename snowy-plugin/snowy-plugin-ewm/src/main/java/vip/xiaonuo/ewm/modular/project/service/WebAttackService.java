package vip.xiaonuo.ewm.modular.project.service;

import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.github.xiaoymin.knife4j.core.util.StrUtil;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.*;
import vip.xiaonuo.ewm.modular.project.param.AttackPortScanPageParam;
import vip.xiaonuo.ewm.modular.project.param.WebAttackPageParam;
import vip.xiaonuo.ewm.modular.project.repository.AttackPortScanRepository;
import vip.xiaonuo.ewm.modular.project.repository.WebAttackRepository;

import java.util.Date;
import java.util.List;

@Service
public class WebAttackService {

    @Autowired
    private WebAttackRepository webAttackRepository;

    @Resource
    private MongoTemplate mongoTemplate;


    public CommonResult<String> save(WebAttackReportRequest webAttackReportRequest) {
        try {
            List<WebAttackLog> logs = webAttackReportRequest.getLogs();
            for (WebAttackLog log : logs) {
                WebAttack webAttack = new WebAttack();
                webAttack.setProjectId(webAttackReportRequest.getProjectId());
                webAttack.setSafeId(webAttackReportRequest.getClientId());
                webAttack.setAttackType(log.getAttackType());
                webAttack.setSourceIp(log.getSourceIp());
                webAttack.setAttackTime(new Date());
                webAttack.setRequestUri(log.getRequestUri());
                webAttack.setRequestMethod(log.getRequestMethod());
                webAttack.setMatchedPattern(log.getMatchedPattern());
                webAttack.setDetectionMethod(log.getDetectionMethod());
                webAttack.setUserAgent(log.getUserAgent());
                webAttack.setReferer(log.getReferer());
                webAttack.setLevel(log.getLevel());
                webAttackRepository.save(webAttack);
            }
            return CommonResult.ok();
        }catch (Exception e){
            return CommonResult.error(e.getMessage());
        }
    }

    public Page<WebAttack> page(WebAttackPageParam param) {
        Query query = new Query();

        // 1. 动态拼接查询条件
        if (ObjectUtil.isNotEmpty(param.getSafeId())) {
            query.addCriteria(Criteria.where("safe_id").is(param.getSafeId()));
        }
        if (StrUtil.isNotBlank(param.getSourceIp())) {
            query.addCriteria(Criteria.where("source_ip").is(param.getSourceIp()));
        }
        if (StrUtil.isNotBlank(param.getLevel())) {
            query.addCriteria(Criteria.where("level").is(param.getLevel()));
        }
        if (StrUtil.isNotBlank(param.getAttackType())) {
            // 支持扫描类型模糊查询 (忽略大小写)
            query.addCriteria(Criteria.where("attack_type").is(param.getAttackType()));
        }

        // 2. 查询符合条件的总记录数
        long total = mongoTemplate.count(query, WebAttack.class);

        // 3. 设置分页和排序 (注意：Spring Data Mongo 的分页页码从 0 开始)
        int current = ObjectUtil.defaultIfNull(param.getCurrent(), 1);
        int size = ObjectUtil.defaultIfNull(param.getSize(), 10);

        // 按照攻击时间倒序排列，最新扫描排在前面
        PageRequest pageRequest = PageRequest.of(current - 1, size, Sort.by(Sort.Direction.DESC, "attack_time"));
        query.with(pageRequest);

        // 4. 查询当前页数据
        List<WebAttack> list = mongoTemplate.find(query, WebAttack.class);

        // 5. 封装为 MyBatis-Plus 的 Page 对象，确保前端 s-table 能正常解析 records 字段
        Page<WebAttack> resultPage = new Page<>(current, size, total);
        resultPage.setRecords(list);

        return resultPage;
    }
}
