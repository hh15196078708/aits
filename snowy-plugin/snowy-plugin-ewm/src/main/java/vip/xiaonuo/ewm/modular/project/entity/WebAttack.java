package vip.xiaonuo.ewm.modular.project.entity;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.util.Date;

@Data
@Document(collection = "web_attack")
public class WebAttack {

    @Id
    private String id;

    //公共参数
    @Field("project_id")
    @NotBlank(message = "项目不能为空")
    private String projectId;

    @Field("safe_id")
    @NotBlank(message = "终端不能为空")
    private String safeId;

    @Field("attack_type")
    private String attackType;

    @Field("attack_time")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date attackTime;

    @Field("source_ip")
    private String sourceIp;

    @Field("level")
    private String level;
    //公共参数

    //web_attack参数
    @Field("request_uri")
    private String requestUri;

    @Field("request_method")
    private String requestMethod;

    //matched_pattern
    @Field("matched_pattern")
    private String matchedPattern;

    //detection_method
    @Field("detection_method")
    private String detectionMethod;

    //user_agent
    @Field("user_agent")
    private String userAgent;

    //referer
    @Field("referer")
    private String referer;
    //web_attack参数


    //dest_port
    @JsonProperty("dest_port")
    private String destPort;

    //protocol
    @JsonProperty("protocol")
    private String protocol;

    //payload_snippet
    @JsonProperty("payload_snippet")
    private String payloadSnippet;


    @Field("scan_type")
    private String scanType;

    @Field("target_ports")
    private String targetPorts;

    @Field("duration")
    private String duration;
}
