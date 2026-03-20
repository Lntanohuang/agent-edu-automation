package com.edu.platform.chat.service;

import com.edu.platform.chat.BaseUnitTest;
import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.event.UserChatMessageEvent;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.*;

@DisplayName("ChatEventPublisher 单元测试")
class ChatEventPublisherTest extends BaseUnitTest {

    @Mock
    private RabbitTemplate rabbitTemplate;

    @InjectMocks
    private ChatEventPublisher publisher;

    @Test
    @DisplayName("发布用户消息到正确的 exchange 和 routing key")
    void publishUserMessage_sendsToCorrectExchangeAndRoutingKey() {
        UserChatMessageEvent event = UserChatMessageEvent.builder()
                .eventId("evt-1").message("你好").build();

        publisher.publishUserMessage(event);

        verify(rabbitTemplate).convertAndSend(
                ChatMqConstants.USER_EXCHANGE,
                ChatMqConstants.USER_ROUTING_KEY,
                event);
    }

    @Test
    @DisplayName("发布 AI 回复到正确的 exchange 和 routing key")
    void publishAiReply_sendsToAiExchange() {
        AiReplyEvent event = AiReplyEvent.builder()
                .eventId("evt-1").answer("回答").build();

        publisher.publishAiReply(event);

        verify(rabbitTemplate).convertAndSend(
                ChatMqConstants.AI_EXCHANGE,
                ChatMqConstants.AI_ROUTING_KEY,
                event);
    }

    @Test
    @DisplayName("RabbitTemplate 异常向上传播")
    void publishUserMessage_propagatesException() {
        UserChatMessageEvent event = UserChatMessageEvent.builder()
                .eventId("evt-1").build();
        doThrow(new AmqpException("连接失败")).when(rabbitTemplate)
                .convertAndSend(anyString(), anyString(), any(UserChatMessageEvent.class));

        assertThatThrownBy(() -> publisher.publishUserMessage(event))
                .isInstanceOf(AmqpException.class)
                .hasMessageContaining("连接失败");
    }
}
