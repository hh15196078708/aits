package vip.xiaonuo.ewm.modular.project.entity;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;
import vip.xiaonuo.common.pojo.CommonEntity;

import java.math.BigDecimal;
import java.util.Date;

@Getter
@Setter
public class EwmProjectList extends EwmProject {

    @Schema(description = "机构名称")
    private String orgName;

}
