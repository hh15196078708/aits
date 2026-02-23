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
import vip.xiaonuo.ewm.modular.project.entity.AttackPortScan;
import vip.xiaonuo.ewm.modular.project.entity.PortScanLog;
import vip.xiaonuo.ewm.modular.project.entity.PortScanReportRequest;
import vip.xiaonuo.ewm.modular.project.param.AttackPortScanPageParam;
import vip.xiaonuo.ewm.modular.project.repository.AttackPortScanRepository;

import java.util.Date;
import java.util.List;

@Service
public class AttackPortScanService {

    @Autowired
    private AttackPortScanRepository attackPortScanRepository;

    @Resource
    private MongoTemplate mongoTemplate;


    public CommonResult<String> save(PortScanReportRequest portScanReportRequest) {
        try {
            List<PortScanLog> logs = portScanReportRequest.getLogs();
            for (PortScanLog log : logs) {
                AttackPortScan attackPortScan = new AttackPortScan();
                attackPortScan.setProjectId(portScanReportRequest.getProjectId());
                attackPortScan.setSafeId(portScanReportRequest.getClientId());
                attackPortScan.setAttackType(log.getAttackType());
                attackPortScan.setSourceIp(log.getSourceIp());
                List<Integer> targetPorts = log.getTargetPorts();
                String targetPortsStr = "";
                //数组转JSON字符串
                if(ObjectUtil.isNotEmpty(targetPorts) && targetPorts.size() > 0){
                    targetPortsStr = targetPorts.toString();
                }
                attackPortScan.setAttackTime(new Date());
                attackPortScan.setTargetPorts(targetPortsStr);
                attackPortScan.setScanType(log.getScanType());
                attackPortScan.setDuration(log.getDuration());
                attackPortScan.setLevel(log.getLevel());
                attackPortScan.setDetectionMethod(log.getDetectionMethod());
                attackPortScanRepository.save(attackPortScan);
            }
            return CommonResult.ok();
        }catch (Exception e){
            return CommonResult.error(e.getMessage());
        }
    }

    public Page<AttackPortScan> page(AttackPortScanPageParam param) {
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
        if (StrUtil.isNotBlank(param.getScanType())) {
            // 支持扫描类型模糊查询 (忽略大小写)
            query.addCriteria(Criteria.where("scan_type").regex(param.getScanType(), "i"));
        }

        // 2. 查询符合条件的总记录数
        long total = mongoTemplate.count(query, AttackPortScan.class);

        // 3. 设置分页和排序 (注意：Spring Data Mongo 的分页页码从 0 开始)
        int current = ObjectUtil.defaultIfNull(param.getCurrent(), 1);
        int size = ObjectUtil.defaultIfNull(param.getSize(), 10);

        // 按照攻击时间倒序排列，最新扫描排在前面
        PageRequest pageRequest = PageRequest.of(current - 1, size, Sort.by(Sort.Direction.DESC, "attack_time"));
        query.with(pageRequest);

        // 4. 查询当前页数据
        List<AttackPortScan> list = mongoTemplate.find(query, AttackPortScan.class);

        // 5. 封装为 MyBatis-Plus 的 Page 对象，确保前端 s-table 能正常解析 records 字段
        Page<AttackPortScan> resultPage = new Page<>(current, size, total);
        resultPage.setRecords(list);

        return resultPage;
    }
}
