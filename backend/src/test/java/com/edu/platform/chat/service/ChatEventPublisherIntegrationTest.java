package com.edu.platform.chat.service;

import com.edu.platform.chat.BaseIntegrationTest;
import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.event.UserChatMessageEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;

import java.util.List;
import java.util.Properties;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/**
 * RabbitMQ 发布集成测试 — 连接真实 RabbitMQ。
 * 禁用消费者自动启动，让消息停留在队列中以便观察。
 * 如果本地 RabbitMQ 未启动则跳过。
 */
@DisplayName("【RabbitMQ 集成】ChatEventPublisher")
@TestPropertySource(properties = "spring.rabbitmq.listener.simple.auto-startup=false")
class ChatEventPublisherIntegrationTest extends BaseIntegrationTest {

    @Autowired
    private ChatEventPublisher publisher;
    @Autowired
    private RabbitTemplate rabbitTemplate;
    @Autowired
    private RabbitAdmin rabbitAdmin;

    @BeforeEach
    void purgeQueues() {
        assumeTrue(com.edu.platform.chat.InfraConditions.isRabbitMqAvailable(),
                "跳过：本地 RabbitMQ 未启动");
        rabbitAdmin.purgeQueue(ChatMqConstants.USER_QUEUE);
        rabbitAdmin.purgeQueue(ChatMqConstants.AI_REPLY_USER_QUEUE);
        rabbitAdmin.purgeQueue(ChatMqConstants.AI_REPLY_PERSIST_QUEUE);
    }

    @Test
    @DisplayName("发布用户消息后，chat.user.queue 中有 1 条消息")
    void publishUserMessage_messageArrivesInQueue() {
        UserChatMessageEvent event = UserChatMessageEvent.builder()
                .eventId("pub-test-1")
                .requestId("req-1")
                .conversationId(1L)
                .userId(100L)
                .message("测试消息")
                .timestamp(System.currentTimeMillis())
                .build();

        publisher.publishUserMessage(event);

        Properties info = rabbitAdmin.getQueueProperties(ChatMqConstants.USER_QUEUE);
        int msgCount = Integer.parseInt(info.getProperty("QUEUE_MESSAGE_COUNT", "0"));

        System.out.println("\n========== [RabbitMQ 发布验证] ==========");
        System.out.println("Exchange: " + ChatMqConstants.USER_EXCHANGE);
        System.out.println("RoutingKey: " + ChatMqConstants.USER_ROUTING_KEY);
        System.out.println("Queue: " + ChatMqConstants.USER_QUEUE);
        System.out.println("队列中消息数: " + msgCount);
        System.out.println("==========================================\n");

        assertThat(msgCount).isEqualTo(1);
    }

    @Test
    @DisplayName("发布 AI 回复后，两个 fanout 队列各收到 1 条消息")
    void publishAiReply_fanoutToBothQueues() {
        AiReplyEvent event = AiReplyEvent.builder()
                .eventId("pub-test-2")
                .requestId("req-2")
                .conversationId(1L)
                .userId(100L)
                .userMessage("问题")
                .answer("AI 回答")
                .tokens(5)
                .success(true)
                .sources(List.of("教材P10"))
                .explorationTasks(List.of())
                .bookLabels(List.of("法理学"))
                .auditNotes(List.of())
                .timestamp(System.currentTimeMillis())
                .build();

        publisher.publishAiReply(event);

        Properties userQueueInfo = rabbitAdmin.getQueueProperties(ChatMqConstants.AI_REPLY_USER_QUEUE);
        Properties persistQueueInfo = rabbitAdmin.getQueueProperties(ChatMqConstants.AI_REPLY_PERSIST_QUEUE);
        int userCount = Integer.parseInt(userQueueInfo.getProperty("QUEUE_MESSAGE_COUNT", "0"));
        int persistCount = Integer.parseInt(persistQueueInfo.getProperty("QUEUE_MESSAGE_COUNT", "0"));

        System.out.println("\n========== [RabbitMQ Fanout 验证] ==========");
        System.out.println("Exchange: " + ChatMqConstants.AI_EXCHANGE);
        System.out.println(ChatMqConstants.AI_REPLY_USER_QUEUE + " 消息数: " + userCount);
        System.out.println(ChatMqConstants.AI_REPLY_PERSIST_QUEUE + " 消息数: " + persistCount);
        System.out.println("一条消息被 fanout 到两个队列 ✓");
        System.out.println("=============================================\n");

        assertThat(userCount).isEqualTo(1);
        assertThat(persistCount).isEqualTo(1);
    }

    @Test
    @DisplayName("从队列中取出消息并反序列化，字段完整")
    void publishUserMessage_serializationRoundTrip() {
        UserChatMessageEvent original = UserChatMessageEvent.builder()
                .eventId("ser-test")
                .requestId("req-ser")
                .conversationId(42L)
                .userId(200L)
                .message("序列化测试")
                .timestamp(1234567890L)
                .build();

        publisher.publishUserMessage(original);

        Object received = rabbitTemplate.receiveAndConvert(ChatMqConstants.USER_QUEUE, 3000);

        System.out.println("\n========== [RabbitMQ 序列化验证] ==========");
        System.out.println("发送类型: " + original.getClass().getSimpleName());
        System.out.println("接收类型: " + (received != null ? received.getClass().getSimpleName() : "null"));
        System.out.println("接收内容: " + received);
        System.out.println("=============================================\n");

        assertThat(received).isInstanceOf(UserChatMessageEvent.class);
        UserChatMessageEvent deserialized = (UserChatMessageEvent) received;
        assertThat(deserialized.getEventId()).isEqualTo("ser-test");
        assertThat(deserialized.getMessage()).isEqualTo("序列化测试");
        assertThat(deserialized.getConversationId()).isEqualTo(42L);
    }
}
