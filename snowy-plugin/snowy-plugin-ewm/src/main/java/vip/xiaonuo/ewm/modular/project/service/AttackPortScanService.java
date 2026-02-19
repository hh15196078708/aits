package vip.xiaonuo.ewm.modular.project.service;

import cn.hutool.core.util.ObjectUtil;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Service;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.entity.AttackPortScan;
import vip.xiaonuo.ewm.modular.project.entity.PortScanLog;
import vip.xiaonuo.ewm.modular.project.entity.PortScanReportRequest;
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
}
