package vip.xiaonuo.ewm.modular.project.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollStreamUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.extra.qrcode.QrCodeUtil;
import cn.hutool.extra.qrcode.QrConfig;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import jakarta.annotation.Resource;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.text.StringEscapeUtils;
import org.apache.poi.util.StringUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import vip.xiaonuo.common.enums.CommonSortOrderEnum;
import vip.xiaonuo.common.exception.CommonException;
import vip.xiaonuo.common.page.CommonPageRequest;
import vip.xiaonuo.common.util.ByteArrayMultipartFile;
import vip.xiaonuo.dev.api.DevFileApi;
import vip.xiaonuo.ewm.modular.project.entity.EwmProject;
import vip.xiaonuo.ewm.modular.project.entity.EwmProjectList;
import vip.xiaonuo.ewm.modular.project.mapper.EwmProjectMapper;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectAddParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectEditParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectIdParam;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectPageParam;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectService;

import java.util.List;

/**
 * 项目表Service接口实现类
 *
 * @author Richai
 * @date  2025/12/24 15:01
 **/
@Service
public class EwmProjectServiceImpl extends ServiceImpl<EwmProjectMapper, EwmProject> implements EwmProjectService {

    @Resource
    private DevFileApi devFileApi;

    @Autowired
    private EwmProjectMapper ewmProjectMapper;
    @Override
    public Page<EwmProjectList> page(EwmProjectPageParam ewmProjectPageParam) {
        Page<EwmProjectList> page = new Page<>(ewmProjectPageParam.getCurrent(), ewmProjectPageParam.getSize());
        return (Page<EwmProjectList>) ewmProjectMapper.selectEwmProjectAndOrgList(page, ewmProjectPageParam);
//        QueryWrapper<EwmProject> queryWrapper = new QueryWrapper<EwmProject>().checkSqlInjection();
//        if(ObjectUtil.isNotEmpty(ewmProjectPageParam.getProjectName())) {
//            queryWrapper.lambda().like(EwmProject::getProjectName, ewmProjectPageParam.getProjectName());
//        }
//        if(ObjectUtil.isNotEmpty(ewmProjectPageParam.getProjectLeader())) {
//            queryWrapper.lambda().like(EwmProject::getProjectLeader, ewmProjectPageParam.getProjectLeader());
//        }
//        if(ObjectUtil.isAllNotEmpty(ewmProjectPageParam.getSortField(), ewmProjectPageParam.getSortOrder())) {
//            CommonSortOrderEnum.validate(ewmProjectPageParam.getSortOrder());
//            queryWrapper.orderBy(true, ewmProjectPageParam.getSortOrder().equals(CommonSortOrderEnum.ASC.getValue()),
//                    StrUtil.toUnderlineCase(ewmProjectPageParam.getSortField()));
//        } else {
//            queryWrapper.lambda().orderByAsc(EwmProject::getSortCode);
//        }
//        return this.page(CommonPageRequest.defaultPage(), queryWrapper);

//        List<EwmProjectList> projectLists = ewmProjectMapper.selectEwmProjectAndOrgList(ewmProjectPageParam);


    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public void add(EwmProjectAddParam ewmProjectAddParam) {
        //判断项目排序码是否为空
        if(ObjectUtil.isEmpty(ewmProjectAddParam.getSortCode())){
            ewmProjectAddParam.setSortCode(99);
        }
        //将projectDesc转义存储
        if(StringUtils.isNotBlank(ewmProjectAddParam.getProjectDesc())){
            ewmProjectAddParam.setProjectDesc(StringEscapeUtils.escapeHtml4(ewmProjectAddParam.getProjectDesc()));
        }
        EwmProject ewmProject = BeanUtil.toBean(ewmProjectAddParam, EwmProject.class);
        this.save(ewmProject);
        String projectId = ewmProject.getId();
        // 2. 配置二维码参数 (宽高 300x300，可根据需求调整)
        QrConfig config = new QrConfig(600, 600);
        config.setMargin(1); // 设置边距
        // 3. 生成二维码的字节数组
        // 这里生成的内容是 projectId，你也可以拼接成完整的 URL，例如: "https://yourdomain.com/project?id=" + projectId
        byte[] qrCodeBytes = QrCodeUtil.generatePng(projectId, config);
        // 4. 将字节数组转换为 MultipartFile 对象
        String fileName = "qrcode_" + projectId + ".png";
        MultipartFile qrCodeFile = new ByteArrayMultipartFile(
                "file",           // 表单中的字段名
                fileName,         // 原始文件名
                "image/png",      // 文件类型
                qrCodeBytes       // 文件字节流
        );
        String dynamicReturnUrl = devFileApi.uploadDynamicReturnUrl(qrCodeFile);
        ewmProject.setProjectEwm(dynamicReturnUrl);
        this.updateById(ewmProject);
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public void edit(EwmProjectEditParam ewmProjectEditParam) {
        if(ObjectUtil.isEmpty(ewmProjectEditParam.getSortCode())){
            ewmProjectEditParam.setSortCode(99);
        }
        //将projectDesc转义存储
        if(StringUtils.isNotBlank(ewmProjectEditParam.getProjectDesc())){
            ewmProjectEditParam.setProjectDesc(StringEscapeUtils.escapeHtml4(ewmProjectEditParam.getProjectDesc()));
        }
        EwmProject ewmProject = this.queryEntity(ewmProjectEditParam.getId());
        BeanUtil.copyProperties(ewmProjectEditParam, ewmProject);
        this.updateById(ewmProject);
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public void delete(List<EwmProjectIdParam> ewmProjectIdParamList) {
        // 执行删除
        this.removeByIds(CollStreamUtil.toList(ewmProjectIdParamList, EwmProjectIdParam::getId));
    }

    @Override
    public EwmProject detail(EwmProjectIdParam ewmProjectIdParam) {
        EwmProject ewmProject = this.queryEntity(ewmProjectIdParam.getId());
        ewmProject.setProjectDesc(StringEscapeUtils.unescapeHtml4(ewmProject.getProjectDesc()));
        return ewmProject;
    }

    @Override
    public EwmProject queryEntity(String id) {
        EwmProject ewmProject = this.getById(id);
        if(ObjectUtil.isEmpty(ewmProject)) {
            throw new CommonException("项目表不存在，id值为：{}", id);
        }
        return ewmProject;
    }

}
