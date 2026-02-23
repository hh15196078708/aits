package vip.xiaonuo.ewm.modular.project.wss;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import jakarta.websocket.*;
import jakarta.websocket.server.PathParam;
import jakarta.websocket.server.ServerEndpoint;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import vip.xiaonuo.ewm.modular.project.param.EwmProjectSafeCheckParam;
import vip.xiaonuo.ewm.modular.project.service.EwmProjectSafeService;

import java.io.IOException;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 安全终端 WebSocket 服务端
 *
 * 连接地址: ws://host:port/safe/init/ws/{clientId}
 *
 * ⚠️  注入说明：
 *   @ServerEndpoint 由 Tomcat 容器管理，每次连接创建新实例，不经过 Spring IoC。
 *   直接在实例字段使用 @Autowired 无效（字段永远为 null）。
 *   正确做法：通过 @Autowired setter 将 Bean 写入静态字段，所有连接实例共享。
 *
 * 客户端 → 服务端消息:
 *   heartbeat — 心跳，携带硬件数据，服务端校验授权后回复 heartbeat_ack
 *
 * 服务端 → 客户端指令（通过 SafeWebSocketService 触发）:
 *   auto_block — 开启/关闭自动IP拉黑
 *   block_ip   — 封禁指定IP
 *   whitelist  — 更新IP白名单
 *   shutdown   — 关机
 */
@Slf4j
@Component
@ServerEndpoint("/safe/init/ws/{clientId}")
public class WebSocketServer {

    // ----------------------------------------------------------------
    // 静态服务引用（Spring 通过 setter 注入，所有 WebSocket 实例共享）
    // ----------------------------------------------------------------

    private static EwmProjectSafeService ewmProjectSafeService;

    /**
     * Spring 启动时通过此 setter 完成注入（赋值给静态字段）。
     * @Component 保证 Spring 容器初始化时调用一次此方法，
     * 之后 Tomcat 为每个连接创建的实例均可通过静态字段访问 Service。
     */
    @Autowired
    public void setEwmProjectSafeService(EwmProjectSafeService service) {
        WebSocketServer.ewmProjectSafeService = service;
    }

    // ----------------------------------------------------------------
    // 在线会话池（clientId -> Session，线程安全）
    // ----------------------------------------------------------------

    private static final ConcurrentHashMap<String, Session> SESSION_POOL = new ConcurrentHashMap<>();

    // ----------------------------------------------------------------
    // 当前连接实例字段
    // ----------------------------------------------------------------

    private Session session;
    private String clientId;

    // ----------------------------------------------------------------
    // 生命周期回调
    // ----------------------------------------------------------------

    @OnOpen
    public void onOpen(Session session, @PathParam("clientId") String clientId) {
        this.session = session;
        this.clientId = clientId;
        SESSION_POOL.put(clientId, session);
        log.info("[WSS] 连接建立 clientId={} 当前在线: {}", clientId, SESSION_POOL.size());
    }

    @OnClose
    public void onClose(@PathParam("clientId") String clientId) {
        SESSION_POOL.remove(clientId);
        try {
            if (ewmProjectSafeService != null) {
                ewmProjectSafeService.updateOnlineStatus(clientId, "OFF");
            }
        } catch (Exception e) {
            log.warn("[WSS] 更新离线状态失败 clientId={}", clientId, e);
        }
        log.info("[WSS] 连接断开 clientId={} 当前在线: {}", clientId, SESSION_POOL.size());
    }

    @OnError
    public void onError(Session session, Throwable error) {
        log.error("[WSS] 连接错误 clientId={} error={}", clientId, error.getMessage());
    }

    // ----------------------------------------------------------------
    // 消息处理
    // ----------------------------------------------------------------

    @OnMessage
    public void onMessage(String message, @PathParam("clientId") String clientId) {
        try {
            JSONObject json = JSON.parseObject(message);
            String type = json.getString("type");
            if ("heartbeat".equals(type)) {
                handleHeartbeat(json, clientId);
            } else {
                log.warn("[WSS] 未知消息类型 type={} clientId={}", type, clientId);
            }
        } catch (Exception e) {
            log.error("[WSS] 消息处理异常 clientId={}", clientId, e);
        }
    }

    /**
     * 处理心跳消息：校验终端授权，更新 MySQL + MongoDB 硬件数据，回复 heartbeat_ack
     */
    private void handleHeartbeat(JSONObject json, String clientId) throws IOException {
        // 安全校验：URL 路径中的 clientId 必须与消息体中的 id 一致，防止伪造
        String msgId = json.getString("id");
        if (!clientId.equals(msgId)) {
            log.warn("[WSS] clientId 与消息 id 不匹配 urlId={} msgId={}", clientId, msgId);
            sendAck(clientId, "expired", "OFF");
            return;
        }

        // 构建校验参数（复用 checkAuth 的校验与硬件更新逻辑）
        EwmProjectSafeCheckParam param = new EwmProjectSafeCheckParam();
        param.setId(json.getString("id"));
        param.setProjectId(json.getString("projectId"));
        param.setSafeCode(json.getString("safeCode"));
        param.setSafeSecret(json.getString("safeSecret"));
        // 硬件数据（客户端传来的值可能是数字或嵌套对象，统一转 String）
        param.setSafeCpu(objToStr(json.get("safeCpu")));
        param.setSafeCpuUsage(objToStr(json.get("safeCpuUsage")));
        param.setSafeMemory(objToStr(json.get("safeMemory")));
        param.setSafeMemoryUsage(objToStr(json.get("safeMemoryUsage")));
        param.setSafeDisk(objToStr(json.get("safeDisk")));
        param.setSafeDiskUsage(objToStr(json.get("safeDiskUsage")));

        // 调用服务层（true=授权有效且已更新数据，false=校验失败）
        boolean valid = ewmProjectSafeService.checkWsHeartbeat(param);
        if (valid) {
            sendAck(clientId, "normal", "ON");
        } else {
            sendAck(clientId, "expired", "OFF");
        }
    }

    // ----------------------------------------------------------------
    // 向客户端发送消息（实例方法，用于心跳 ack）
    // ----------------------------------------------------------------

    private void sendAck(String clientId, String authStatus, String safeStatus) throws IOException {
        JSONObject ack = new JSONObject();
        ack.put("type", "heartbeat_ack");
        ack.put("authStatus", authStatus);
        ack.put("safeStatus", safeStatus);
        sendToClient(clientId, ack.toJSONString());
    }

    private void sendToClient(String clientId, String message) throws IOException {
        Session s = SESSION_POOL.get(clientId);
        if (s != null && s.isOpen()) {
            synchronized (s) {
                s.getBasicRemote().sendText(message);
            }
        }
    }

    // ----------------------------------------------------------------
    // 静态方法：服务端主动推送指令（由 SafeWebSocketService 调用）
    // ----------------------------------------------------------------

    /**
     * 向指定客户端推送 JSON 指令（线程安全，可从任意 Spring 线程调用）
     *
     * @param clientId 目标终端 ID（即 ewm_project_safe.id）
     * @param message  JSON 指令字符串
     * @return true=推送成功，false=客户端不在线
     */
    public static boolean push(String clientId, String message) {
        Session s = SESSION_POOL.get(clientId);
        if (s == null || !s.isOpen()) {
            log.warn("[WSS] 推送失败，客户端不在线 clientId={}", clientId);
            return false;
        }
        try {
            // getAsyncRemote 线程安全，允许跨线程并发调用
            s.getAsyncRemote().sendText(message);
            return true;
        } catch (Exception e) {
            log.error("[WSS] 推送异常 clientId={}", clientId, e);
            return false;
        }
    }

    /** 判断指定客户端是否在线 */
    public static boolean isOnline(String clientId) {
        Session s = SESSION_POOL.get(clientId);
        return s != null && s.isOpen();
    }

    /** 返回所有在线客户端 ID 集合（只读视图） */
    public static Set<String> getOnlineClientIds() {
        return SESSION_POOL.keySet();
    }

    // ----------------------------------------------------------------
    // 工具方法
    // ----------------------------------------------------------------

    /**
     * 将任意对象转为字符串
     *  - JSONObject → toJSONString()（safeCpu 等嵌套对象字段）
     *  - 数字/布尔  → String.valueOf()（safeCpuUsage 等数值字段）
     *  - String    → 原样返回
     */
    private static String objToStr(Object obj) {
        if (obj == null) return null;
        if (obj instanceof String) return (String) obj;
        if (obj instanceof JSONObject) return ((JSONObject) obj).toJSONString();
        return String.valueOf(obj);
    }
}
