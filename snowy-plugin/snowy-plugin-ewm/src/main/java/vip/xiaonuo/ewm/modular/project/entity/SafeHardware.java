package vip.xiaonuo.ewm.modular.project.entity;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.util.Date;


@Data
@Document(collection = "safe_hardware")
public class SafeHardware {
    @Id
    private String id;

    @Field("safe_id")
    private String safeId;

    @Field("project_id")
    private String projectId;

    @Field("safe_cpu")
    private String safeCpu;

    //SAFE_CPU_USAGE
    @Field("safe_cpu_usage")
    private String safeCpuUsage;

    //SAFE_MEMORY
    @Field("safe_memory")
    private String safeMemory;

    //SAFE_MEMORY_USAGE
    @Field("safe_memory_usage")
    private String safeMemoryUsage;

    //SAFE_DISK
    @Field("safe_disk")
    private String safeDisk;

    //SAFE_DISK_USAGE
    @Field("safe_disk_usage")
    private String safeDiskUsage;

    @Field("create_time")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date createTime;

    @Field("safe_os")
    private String safeOs;

    @Field("safe_ip")
    private String safeIp;

    @Field("safe_name")
    private String safeName;
}
