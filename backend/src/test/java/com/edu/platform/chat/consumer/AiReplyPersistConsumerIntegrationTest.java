package com.edu.platform.chat.consumer;

import com.edu.platform.chat.BaseIntegrationTest;
import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.service.ChatEventPublisher;
import com.edu.platform.chat.service.ChatPendingReplyRegistry;
import com.edu.platform.chat.service.ChatWebSocketNotifier;
import com.edu.platform.dto.ChatMessageResponse;
import com.edu.platform.entity.Conversation;
import com.edu.platform.entity.Message;
import com.edu.platform.repository.ConversationRepository;
import com.edu.platform.repository.MessageRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;

import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;
import static org.awaitility.Awaitility.await;

/**
 * AiReplyPersistConsumer 集成测试 — 验证消息经 MQ 消费后真正写入 H2 和 Redis。
 */
@DisplayName("【MQ 端到端】AiReplyPersistConsumer 持久化")
class AiReplyPersistConsumerIntegrationTest extends BaseIntegrationTest {

    @Autowired
    private ChatEventPublisher publisher;
    @Autowired
    private MessageRepository messageRepository;
    @Autowired
    private ConversationRepository conversationRepository;
    @Autowired
    private ChatPendingReplyRegistry pendingReplyRegistry;
    @Autowired
    private RabbitAdmin rabbitAdmin;

    @MockBean
    private ChatWebSocketNotifier webSocketNotifier;

    private Long testConversationId;

    @BeforeEach
    void setupData() {
        assumeTrue(com.edu.platform.chat.InfraConditions.isRabbitMqAvailable(),
                "跳过：本地 RabbitMQ 未启动");

        messageRepository.deleteAll();
        conversationRepository.deleteAll();

        rabbitAdmin.purgeQueue(ChatMqConstants.AI_REPLY_USER_QUEUE);
        rabbitAdmin.purgeQueue(ChatMqConstants.AI_REPLY_PERSIST_QUEUE);

        // 在 H2 中创建一条 Conversation 记录
        Conversation conv = new Conversation();
        conv.setUserId(100L);
        conv.setTitle("测试会话");
        conv.setMessageCount(0);
        conv = conversationRepository.save(conv);
        testConversationId = conv.getId();
    }

    private AiReplyEvent buildReplyEvent(String eventId) {
        return AiReplyEvent.builder()
                .eventId(eventId)
                .requestId("req-" + eventId)
                .traceId("trace-" + eventId)
                .conversationId(testConversationId)
                .userId(100L)
                .userMessage("什么是法律渊源？")
                .answer("法律渊源是指法的表现形式。")
                .tokens(15)
                .skillUsed("law_explain")
                .sources(List.of("法理学教材P45"))
                .explorationTasks(List.of())
                .bookLabels(List.of("法理学"))
                .confidence("high")
                .auditNotes(List.of())
                .success(true)
                .timestamp(System.currentTimeMillis())
                .build();
    }

    @Test
    @DisplayName("MQ 消费后，H2 数据库中有 user + assistant 两条消息")
    void persistsUserAndAssistantMessages() {
        String eventId = "persist-" + UUID.randomUUID().toString().substring(0, 8);
        publisher.publishAiReply(buildReplyEvent(eventId));

        await("等待持久化完成").atMost(10, TimeUnit.SECONDS).until(() ->
                messageRepository.countByConversationId(testConversationId) >= 2);

        List<Message> msgs = messageRepository.findByConversationIdOrderByCreatedAtAsc(testConversationId);

        System.out.println("\n========== [H2 数据库验证] ==========");
        System.out.println("ConversationId: " + testConversationId);
        System.out.println("消息数量: " + msgs.size());
        for (Message msg : msgs) {
            System.out.println("  [" + msg.getRole() + "] " + msg.getContent().substring(0, Math.min(30, msg.getContent().length())) + "...");
        }
        System.out.println("======================================\n");

        assertThat(msgs).hasSize(2);
        assertThat(msgs.get(0).getRole()).isEqualTo(Message.Role.user);
        assertThat(msgs.get(0).getContent()).isEqualTo("什么是法律渊源？");
        assertThat(msgs.get(1).getRole()).isEqualTo(Message.Role.assistant);
        assertThat(msgs.get(1).getContent()).isEqualTo("法律渊源是指法的表现形式。");
    }

    @Test
    @DisplayName("MQ 消费后，Redis 缓存中追加了两条消息")
    void appendsToRedisCache() {
        String eventId = "cache-" + UUID.randomUUID().toString().substring(0, 8);
        publisher.publishAiReply(buildReplyEvent(eventId));

        await("等待 Redis 缓存更新").atMost(10, TimeUnit.SECONDS).until(() -> {
            Long size = redisTemplate.opsForList().size("chat:session:" + testConversationId + ":messages");
            return size != null && size >= 2;
        });

        List<String> raw = redisTemplate.opsForList().range(
                "chat:session:" + testConversationId + ":messages", 0, -1);

        System.out.println("\n========== [Redis 缓存验证] ==========");
        System.out.println("Key: chat:session:" + testConversationId + ":messages");
        System.out.println("缓存条目数: " + (raw != null ? raw.size() : 0));
        if (raw != null) {
            for (String item : raw) {
                System.out.println("  " + item.substring(0, Math.min(60, item.length())) + "...");
            }
        }
        System.out.println("=======================================\n");

        assertThat(raw).hasSize(2);
        assertThat(raw.get(0)).contains("\"role\":\"user\"");
        assertThat(raw.get(1)).contains("\"role\":\"assistant\"");
    }

    @Test
    @DisplayName("CompletableFuture 收到响应（MQ 异步 → 同步桥接）")
    void completesCompletableFuture() throws Exception {
        String eventId = "future-" + UUID.randomUUID().toString().substring(0, 8);
        AiReplyEvent event = buildReplyEvent(eventId);

        // 先注册 future，模拟 ChatService.sendMessage 的行为
        CompletableFuture<ChatMessageResponse> future = pendingReplyRegistry.register(event.getRequestId());

        System.out.println("\n========== [CompletableFuture 同步桥接] ==========");
        System.out.println("已注册 Future, requestId: " + event.getRequestId());

        publisher.publishAiReply(event);
        System.out.println("已发布 AiReplyEvent → MQ");

        // 真实阻塞等待消费者处理完成
        ChatMessageResponse response = future.get(10, TimeUnit.SECONDS);

        System.out.println("Future 已 complete!");
        System.out.println("响应内容: " + response.getContent());
        System.out.println("技能: " + response.getSkillUsed());
        System.out.println("来源: " + response.getSources());
        System.out.println("===================================================\n");

        assertThat(response.getContent()).isEqualTo("法律渊源是指法的表现形式。");
        assertThat(response.getSkillUsed()).isEqualTo("law_explain");
        assertThat(response.getSources()).containsExactly("法理学教材P45");
    }

    @Test
    @DisplayName("幂等：同一 eventId 持久化两次，DB 只有 2 条消息")
    void idempotency_secondEventSkipped() {
        String eventId = "idem-" + UUID.randomUUID().toString().substring(0, 8);
        AiReplyEvent event = buildReplyEvent(eventId);

        publisher.publishAiReply(event);
        await().atMost(10, TimeUnit.SECONDS).until(() ->
                messageRepository.countByConversationId(testConversationId) >= 2);

        // 再发一条相同 eventId
        publisher.publishAiReply(event);
        try { Thread.sleep(1500); } catch (InterruptedException ignored) {}

        long count = messageRepository.countByConversationId(testConversationId);

        System.out.println("\n========== [持久化幂等验证] ==========");
        System.out.println("发送 2 次相同 eventId: " + eventId);
        System.out.println("DB 消息数: " + count + " (应为 2，不是 4)");
        System.out.println("======================================\n");

        assertThat(count).isEqualTo(2);
    }
}
