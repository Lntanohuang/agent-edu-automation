package com.edu.platform.chat.consumer;

import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.service.ChatWebSocketNotifier;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "chat.mq", name = "enabled", havingValue = "true")
public class AiReplyDeliveryConsumer {

    private final ChatWebSocketNotifier webSocketNotifier;

    @RabbitListener(queues = ChatMqConstants.AI_REPLY_USER_QUEUE)
    public void consume(AiReplyEvent event) {
        if (event == null || event.getEventId() == null) {
            return;
        }
        webSocketNotifier.pushToUser(event);
        log.debug("已推送 AI 回复到用户通道: requestId={}", event.getRequestId());
    }
}
