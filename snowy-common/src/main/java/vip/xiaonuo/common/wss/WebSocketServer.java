package vip.xiaonuo.common.wss;

import jakarta.websocket.*;
import jakarta.websocket.server.PathParam;
import jakarta.websocket.server.ServerEndpoint;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@ServerEndpoint("/waf/ws/{userId}")
public class WebSocketServer {

    // 静态变量，用来记录当前在线连接数。应该设计为线程安全的。
    private static final ConcurrentHashMap<String, Session> SESSION_POOL = new ConcurrentHashMap<>();

    /**
     * 连接建立成功调用的方法
     */
    @OnOpen
    public void onOpen(Session session, @PathParam("userId") String userId) {
        try {
            SESSION_POOL.put(userId, session);
            log.info("【WebSocket】有新的连接，总数: {}", SESSION_POOL.size());
            log.info("【WebSocket】用户ID: {}", userId);

            // 可以在连接建立时给客户端发个欢迎消息
            sendMessageToUser(userId, "连接成功，欢迎用户: " + userId);
        } catch (Exception e) {
            log.error("【WebSocket】连接异常", e);
        }
    }

    /**
     * 连接关闭调用的方法
     */
    @OnClose
    public void onClose(Session session, @PathParam("userId") String userId) {
        SESSION_POOL.remove(userId);
        log.info("【WebSocket】连接断开，用户ID: {}，当前在线人数: {}", userId, SESSION_POOL.size());
    }

    /**
     * 收到客户端消息后调用的方法
     *
     * @param message 客户端发送过来的消息
     */
    @OnMessage
    public void onMessage(String message, Session session, @PathParam("userId") String userId) {
        log.info("【WebSocket】收到用户 {} 的消息: {}", userId, message);

        // 这里可以根据业务逻辑处理消息，比如解析JSON指令
        if ("ping".equalsIgnoreCase(message)) {
            sendMessageToUser(userId, "pong"); // 心跳回复
        }
    }

    /**
     * 发生错误时调用
     */
    @OnError
    public void onError(Session session, Throwable error) {
        log.error("【WebSocket】发生错误", error);
    }

    /**
     * 实现服务器主动推送：向指定用户发送消息
     */
    public void sendMessageToUser(String userId, String message) {
        Session session = SESSION_POOL.get(userId);
        if (session != null && session.isOpen()) {
            try {
                // synchronized防止并发发送导致异常
                synchronized (session) {
                    session.getBasicRemote().sendText(message);
                }
                log.info("【WebSocket】向用户 {} 发送消息成功: {}", userId, message);
            } catch (IOException e) {
                log.error("【WebSocket】发送消息失败", e);
            }
        } else {
            log.warn("【WebSocket】用户 {} 不在线或连接已关闭", userId);
        }
    }

    /**
     * 广播消息：向所有在线用户发送
     */
    public void sendAllMessage(String message) {
        log.info("【WebSocket】广播消息: {}", message);
        SESSION_POOL.forEach((userId, session) -> {
            if (session.isOpen()) {
                try {
                    synchronized (session) {
                        session.getBasicRemote().sendText(message);
                    }
                } catch (IOException e) {
                    log.error("【WebSocket】广播发送异常", e);
                }
            }
        });
    }

}
