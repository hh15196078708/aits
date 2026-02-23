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
}
