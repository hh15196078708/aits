package vip.xiaonuo.filemanger.modular.files.service;

import cn.hutool.json.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.filemanger.modular.files.entity.SysFiles;
import vip.xiaonuo.filemanger.modular.files.param.FileVO;
import vip.xiaonuo.filemanger.modular.files.param.MergeRequest;

import java.io.IOException;
import java.util.List;

/**
 * 文件管理表Service接口
 *
 * @author Richai
 * @date  2026/01/30 17:35
 **/
public interface SysFilesService extends IService<SysFiles> {

    void createFolder(SysFiles files);

    CommonResult<String> uploadChunk(MultipartFile chunk,
                                     @RequestParam("hash") String hash,
                                     @RequestParam("index") Integer index) throws IOException;

    CommonResult<FileVO> mergeChunks(MergeRequest mergeRequest) throws IOException;

}
