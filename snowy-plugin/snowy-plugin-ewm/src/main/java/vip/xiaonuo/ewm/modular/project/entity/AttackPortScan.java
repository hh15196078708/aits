package vip.xiaonuo.ewm.modular.project.entity;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.util.Date;

@Data
@Document(collection = "attack_port_scan")
public class AttackPortScan {

    @Id
    private String id;

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

    @Field("scan_type")
    private String scanType;

    @Field("level")
    private String level;

    @Field("detection_method")
    private String detectionMethod;

    @Field("target_ports")
    private String targetPorts;

    @Field("duration")
    private String duration;
}
