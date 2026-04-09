package com.edu.platform.chat.service;

import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.event.UserChatMessageEvent;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "chat.mq", name = "enabled", havingValue = "true")
public class ChatEventPublisher {

    private final RabbitTemplate rabbitTemplate;

    public void publishUserMessage(UserChatMessageEvent event) {
        rabbitTemplate.convertAndSend(ChatMqConstants.USER_EXCHANGE, ChatMqConstants.USER_ROUTING_KEY, event);
    }

    public void publishAiReply(AiReplyEvent event) {
        rabbitTemplate.convertAndSend(ChatMqConstants.AI_EXCHANGE, ChatMqConstants.AI_ROUTING_KEY, event);
    }
}
