package vip.xiaonuo.ewm.modular.project.service;

import com.alibaba.fastjson.JSONObject;
import org.springframework.stereotype.Service;
import vip.xiaonuo.common.pojo.CommonResult;
import vip.xiaonuo.ewm.modular.project.param.WsAutoBlockParam;
import vip.xiaonuo.ewm.modular.project.param.WsBlockIpParam;
import vip.xiaonuo.ewm.modular.project.param.WsClientIdParam;
import vip.xiaonuo.ewm.modular.project.param.WsWhitelistParam;
import vip.xiaonuo.ewm.modular.project.wss.WebSocketServer;

/**
 * 安全终端 WebSocket 指令推送服务
 * <p>
 * 封装四类服务端主动下发指令，通过 {@link WebSocketServer#push} 推送给在线终端。
 */
@Service
public class SafeWebSocketService {

    /**
     * 下发自动拉黑开关指令
     *
     * @param param clientId + enabled
     */
    public CommonResult<String> sendAutoBlock(WsAutoBlockParam param) {
        JSONObject msg = new JSONObject();
        msg.put("type", "auto_block");
        msg.put("enabled", param.getEnabled());
        return doPush(param.getClientId(), msg.toJSONString());
    }

    /**
     * 下发封禁指定IP指令
     *
     * @param param clientId + ip
     */
    public CommonResult<String> sendBlockIp(WsBlockIpParam param) {
        JSONObject msg = new JSONObject();
        msg.put("type", "block_ip");
        msg.put("ip", param.getIp());
        return doPush(param.getClientId(), msg.toJSONString());
    }

    /**
     * 下发IP白名单更新指令
     *
     * @param param clientId + ips
     */
    public CommonResult<String> sendWhitelist(WsWhitelistParam param) {
        JSONObject msg = new JSONObject();
        msg.put("type", "whitelist");
        msg.put("ips", param.getIps());
        return doPush(param.getClientId(), msg.toJSONString());
    }

    /**
     * 下发关机指令
     *
     * @param param clientId
     */
    public CommonResult<String> sendShutdown(WsClientIdParam param) {
        JSONObject msg = new JSONObject();
        msg.put("type", "shutdown");
        return doPush(param.getClientId(), msg.toJSONString());
    }

    // ----------------------------------------------------------------

    private CommonResult<String> doPush(String clientId, String message) {
        if (!WebSocketServer.isOnline(clientId)) {
            return CommonResult.error("终端不在线，指令下发失败");
        }
        boolean success = WebSocketServer.push(clientId, message);
        return success ? CommonResult.ok("指令已下发") : CommonResult.error("指令下发失败");
    }
}
