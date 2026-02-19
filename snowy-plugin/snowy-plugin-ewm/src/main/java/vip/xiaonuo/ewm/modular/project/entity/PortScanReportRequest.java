package vip.xiaonuo.ewm.modular.project.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
public class PortScanReportRequest {
    private String projectId;

    @JsonProperty("clientId") // 映射 JSON 中的 client_id
    private String clientId;

    private List<PortScanLog> logs;
}
