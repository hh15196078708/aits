package vip.xiaonuo.ewm.modular.project.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
public class PortScanLog {
    @JsonProperty("attack_type")
    private String attackType;

    @JsonProperty("source_ip")
    private String sourceIp;

    @JsonProperty("target_ports")
    private List<Integer> targetPorts;

    @JsonProperty("port_count")
    private Integer portCount;

    @JsonProperty("scan_type")
    private String scanType;

    @JsonProperty("duration")
    private String duration;

    @JsonProperty("level")
    private String level;

    @JsonProperty("detection_method")
    private String detectionMethod;
}
