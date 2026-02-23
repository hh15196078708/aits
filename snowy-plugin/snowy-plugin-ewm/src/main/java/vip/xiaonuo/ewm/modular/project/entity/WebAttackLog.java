package vip.xiaonuo.ewm.modular.project.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
public class WebAttackLog {
    @JsonProperty("attack_type")
    private String attackType;

    @JsonProperty("source_ip")
    private String sourceIp;

    @JsonProperty("request_uri")
    private String requestUri;

    @JsonProperty("request_method")
    private String requestMethod;

    @JsonProperty("matched_pattern")
    private String matchedPattern;

    @JsonProperty("timestamp")
    private String timestamp;

    @JsonProperty("level")
    private String level;

    @JsonProperty("detection_method")
    private String detectionMethod;

    @JsonProperty("user_agent")
    private String userAgent;

    @JsonProperty("referer")
    private String referer;

    //dest_port
    @JsonProperty("dest_port")
    private String destPort;

    //protocol
    @JsonProperty("protocol")
    private String protocol;

    //payload_snippet
    @JsonProperty("payload_snippet")
    private String payloadSnippet;

    @JsonProperty("target_ports")
    private List<Integer> targetPorts;

    @JsonProperty("port_count")
    private Integer portCount;

    @JsonProperty("scan_type")
    private String scanType;

    @JsonProperty("duration")
    private String duration;

}
