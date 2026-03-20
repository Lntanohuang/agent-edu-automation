package com.edu.platform.chat.consumer;

import com.edu.platform.chat.BaseIntegrationTest;
import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.UserChatMessageEvent;
import com.edu.platform.chat.service.AiModelClient;
import com.edu.platform.chat.service.ChatContextCacheService;
import com.edu.platform.chat.service.ChatEventPublisher;
import com.edu.platform.chat.service.ChatWebSocketNotifier;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;

import java.util.List;
import java.util.UUID;

import static java.util.concurrent.TimeUnit.SECONDS;
import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.mockito.ArgumentMatchers.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;
import static org.mockito.Mockito.*;

/**
 * 端到端 MQ 流转集成测试 — 核心测试。
 * 真实 RabbitMQ + 真实 Redis，AI 服务用 @MockBean 替代。
 *
 * 你可以在控制台看到消息从发布 → 消费 → Redis 写入的全过程。
 */
@DisplayName("【MQ 端到端】UserMessageConsumer 流转")
class UserMessageConsumerIntegrationTest extends BaseIntegrationTest {

    @Autowired
    private ChatEventPublisher publisher;
    @Autowired
    private ChatContextCacheService cacheService;
    @Autowired
    private RabbitAdmin rabbitAdmin;

    @MockBean
    private AiModelClient aiModelClient;
    @MockBean
    private ChatWebSocketNotifier webSocketNotifier;

    @BeforeEach
    void purgeQueues() {
        assumeTrue(com.edu.platform.chat.InfraConditions.isRabbitMqAvailable(),
                "跳过：本地 RabbitMQ 未启动");
        rabbitAdmin.purgeQueue(ChatMqConstants.USER_QUEUE);
        rabbitAdmin.purgeQueue(ChatMqConstants.AI_REPLY_USER_QUEUE);
        rabbitAdmin.purgeQueue(ChatMqConstants.AI_REPLY_PERSIST_QUEUE);
    }

    private UserChatMessageEvent buildEvent(String eventId) {
        return UserChatMessageEvent.builder()
                .eventId(eventId)
                .requestId("req-" + eventId)
                .traceId("trace-" + eventId)
                .conversationId(999L)
                .userId(100L)
                .message("什么是法律渊源？")
                .timestamp(System.currentTimeMillis())
                .build();
    }

    @Test
    @DisplayName("完整流转：用户消息 → MQ → Consumer → 调 AI → 发布 AI 回复")
    void fullFlow_userMessageToAiReply() {
        String eventId = "flow-" + UUID.randomUUID().toString().substring(0, 8);

        when(aiModelClient.generateReply(anyString(), anyLong(), anyList()))
                .thenReturn(new AiModelClient.AiServiceReply(
                        "法律渊源是法的表现形式", "law_explain",
                        List.of("法理学教材P45"), List.of(), List.of("法理学"),
                        "high", List.of()));

        long start = System.currentTimeMillis();
        System.out.println("\n========== [MQ 端到端流转] 开始 ==========");
        System.out.println("EventId: " + eventId);

        publisher.publishUserMessage(buildEvent(eventId));
        System.out.println("[1] 已发布 UserChatMessageEvent → " + ChatMqConstants.USER_EXCHANGE);

        // 等待 UserMessageConsumer 处理（幂等 key 出现）
        await("等待 UserMessageConsumer 写入幂等 key")
                .atMost(10, SECONDS)
                .pollInterval(200, java.util.concurrent.TimeUnit.MILLISECONDS)
                .until(() -> Boolean.TRUE.equals(
                        redisTemplate.hasKey("chat:msg:digest:user-consume:" + eventId)));

        System.out.println("[2] UserMessageConsumer 已处理 (Redis 幂等 key 已写入)");

        // 等待 AiReplyPersistConsumer 处理（persist 幂等 key 出现）
        await("等待 AiReplyPersistConsumer 写入幂等 key")
                .atMost(10, SECONDS)
                .pollInterval(200, java.util.concurrent.TimeUnit.MILLISECONDS)
                .until(() -> Boolean.TRUE.equals(
                        redisTemplate.hasKey("chat:msg:digest:persist-consume:" + eventId)));

        long elapsed = System.currentTimeMillis() - start;
        System.out.println("[3] AiReplyPersistConsumer 已处理 (消息已持久化)");
        System.out.println("[4] 全链路耗时: " + elapsed + "ms");
        System.out.println("==========================================\n");

        verify(aiModelClient, timeout(5000)).generateReply(eq("什么是法律渊源？"), eq(999L), anyList());
    }

    @Test
    @DisplayName("幂等：同一 eventId 发两次，AI 只调用一次")
    void idempotency_duplicateEventSkipped() {
        String eventId = "dup-" + UUID.randomUUID().toString().substring(0, 8);

        when(aiModelClient.generateReply(anyString(), anyLong(), anyList()))
                .thenReturn(new AiModelClient.AiServiceReply(
                        "回答", "law_explain", List.of(), List.of(), List.of(), "high", List.of()));

        publisher.publishUserMessage(buildEvent(eventId));
        // 等第一条处理完
        await().atMost(10, SECONDS).until(() ->
                Boolean.TRUE.equals(redisTemplate.hasKey("chat:msg:digest:user-consume:" + eventId)));

        // 再发一条相同 eventId
        publisher.publishUserMessage(buildEvent(eventId));
        // 稍等让第二条被消费
        try { Thread.sleep(1000); } catch (InterruptedException ignored) {}

        System.out.println("\n========== [MQ 幂等验证] ==========");
        System.out.println("EventId: " + eventId);
        System.out.println("发送了 2 次，AI 应只被调用 1 次");
        System.out.println("====================================\n");

        verify(aiModelClient, times(1)).generateReply(anyString(), anyLong(), anyList());
    }

    @Test
    @DisplayName("AI 失败时发布 fallback 回复，不抛异常")
    void whenAiFails_publishesFallback() {
        String eventId = "fail-" + UUID.randomUUID().toString().substring(0, 8);

        when(aiModelClient.generateReply(anyString(), anyLong(), anyList()))
                .thenThrow(new RuntimeException("AI 连接超时"));

        publisher.publishUserMessage(buildEvent(eventId));

        await("等待 fallback 处理完成").atMost(10, SECONDS).until(() ->
                Boolean.TRUE.equals(redisTemplate.hasKey("chat:msg:digest:persist-consume:" + eventId)));

        System.out.println("\n========== [MQ Fallback 验证] ==========");
        System.out.println("AI 调用失败，但 fallback 消息成功流转并持久化");
        System.out.println("persist 幂等 key 存在: " + redisTemplate.hasKey("chat:msg:digest:persist-consume:" + eventId));
        System.out.println("=========================================\n");

        // fallback 消息应该成功流转到 persist consumer
        assertThat(redisTemplate.hasKey("chat:msg:digest:persist-consume:" + eventId)).isTrue();
    }
}
