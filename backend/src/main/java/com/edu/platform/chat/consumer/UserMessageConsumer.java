package com.edu.platform.chat.consumer;

import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.event.UserChatMessageEvent;
import com.edu.platform.chat.service.AiModelClient;
import com.edu.platform.chat.service.ChatContextCacheService;
import com.edu.platform.chat.service.ChatEventPublisher;
import com.edu.platform.common.BusinessException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "chat.mq", name = "enabled", havingValue = "true")
public class UserMessageConsumer {

    private static final int HISTORY_LIMIT = 20;

    private final ChatContextCacheService cacheService;
    private final AiModelClient aiModelClient;
    private final ChatEventPublisher eventPublisher;

    @RabbitListener(queues = ChatMqConstants.USER_QUEUE)
    public void consume(UserChatMessageEvent event) {
        if (event == null || event.getEventId() == null) {
            return;
        }

        String digestId = "user-consume:" + event.getEventId();
        if (!cacheService.markEventProcessed(digestId)) {
            log.info("跳过重复用户消息事件: {}", event.getEventId());
            return;
        }

        AiReplyEvent replyEvent;
        try {
            List<ChatContextCacheService.HistoryMessage> history =
                    cacheService.loadHistory(event.getConversationId(), HISTORY_LIMIT);

            AiModelClient.AiServiceReply aiReply =
                    aiModelClient.generateReply(event.getMessage(), event.getConversationId(), history);

            replyEvent = AiReplyEvent.builder()
                    .eventId(event.getEventId())
                    .requestId(event.getRequestId())
                    .traceId(event.getTraceId())
                    .conversationId(event.getConversationId())
                    .userId(event.getUserId())
                    .userMessage(event.getMessage())
                    .answer(aiReply.answer())
                    .tokens(aiReply.answer() == null ? 0 : aiReply.answer().length() / 2)
                    .skillUsed(aiReply.skillUsed())
                    .sources(aiReply.sources())
                    .explorationTasks(aiReply.explorationTasks())
                    .bookLabels(aiReply.bookLabels())
                    .confidence(aiReply.confidence())
                    .auditNotes(aiReply.auditNotes())
                    .success(Boolean.TRUE)
                    .timestamp(System.currentTimeMillis())
                    .build();
        } catch (BusinessException e) {
            replyEvent = fallbackReply(event, e.getMessage());
        } catch (Exception e) {
            log.error("处理用户消息事件失败: {}", event.getEventId(), e);
            replyEvent = fallbackReply(event, "AI 服务暂时不可用，请稍后再试");
        }

        try {
            eventPublisher.publishAiReply(replyEvent);
        } catch (Exception e) {
            cacheService.clearEventDigest(digestId);
            throw e;
        }
    }

    private AiReplyEvent fallbackReply(UserChatMessageEvent event, String reason) {
        return AiReplyEvent.builder()
                .eventId(event.getEventId())
                .requestId(event.getRequestId())
                .traceId(event.getTraceId())
                .conversationId(event.getConversationId())
                .userId(event.getUserId())
                .userMessage(event.getMessage())
                .answer("AI 服务暂时不可用，请稍后再试")
                .tokens(0)
                .sources(List.of())
                .explorationTasks(List.of())
                .bookLabels(List.of())
                .auditNotes(List.of())
                .success(Boolean.FALSE)
                .errorMessage(reason)
                .timestamp(System.currentTimeMillis())
                .build();
    }
}
