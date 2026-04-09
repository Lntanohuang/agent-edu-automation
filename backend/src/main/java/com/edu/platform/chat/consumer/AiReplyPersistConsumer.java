package com.edu.platform.chat.consumer;

import com.alibaba.fastjson2.JSON;
import com.edu.platform.chat.config.ChatMqConstants;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.mongo.ChatMessageArchive;
import com.edu.platform.chat.service.ChatContextCacheService;
import com.edu.platform.chat.service.ChatMongoArchiveService;
import com.edu.platform.chat.service.ChatPendingReplyRegistry;
import com.edu.platform.chat.service.ChatWebSocketNotifier;
import com.edu.platform.dto.ChatMessageResponse;
import com.edu.platform.entity.Message;
import com.edu.platform.repository.ConversationRepository;
import com.edu.platform.repository.MessageRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "chat.mq", name = "enabled", havingValue = "true")
public class AiReplyPersistConsumer {

    private final MessageRepository messageRepository;
    private final ConversationRepository conversationRepository;
    private final ChatContextCacheService cacheService;
    private final ChatMongoArchiveService mongoArchiveService;
    private final ChatPendingReplyRegistry pendingReplyRegistry;
    private final ChatWebSocketNotifier webSocketNotifier;

    @RabbitListener(queues = ChatMqConstants.AI_REPLY_PERSIST_QUEUE)
    @Transactional
    public void consume(AiReplyEvent event) {
        if (event == null || event.getEventId() == null) {
            return;
        }

        String digestId = "persist-consume:" + event.getEventId();
        if (!cacheService.markEventProcessed(digestId)) {
            log.info("跳过重复 AI 回复持久化事件: {}", event.getEventId());
            return;
        }

        try {
            Message userMessage = saveUserMessage(event);
            Message aiMessage = saveAssistantMessage(event);

            conversationRepository.incrementMessageCount(event.getConversationId());
            conversationRepository.incrementMessageCount(event.getConversationId());

            cacheService.appendUserMessage(event.getConversationId(), event.getUserMessage());
            cacheService.appendAssistantMessage(event.getConversationId(), event.getAnswer(), aiMessage.getTokensUsed());

            archiveToMongo(event);
            webSocketNotifier.pushToAdmin(event);

            pendingReplyRegistry.complete(event.getRequestId(), toResponse(aiMessage, event));
            log.debug("AI 回复持久化完成: requestId={}", event.getRequestId());
        } catch (Exception e) {
            cacheService.clearEventDigest(digestId);
            pendingReplyRegistry.completeExceptionally(event.getRequestId(), e);
            throw e;
        }
    }

    private Message saveUserMessage(AiReplyEvent event) {
        Message message = new Message();
        message.setConversationId(event.getConversationId());
        message.setRole(Message.Role.user);
        message.setContent(event.getUserMessage());
        return messageRepository.save(message);
    }

    private Message saveAssistantMessage(AiReplyEvent event) {
        Message message = new Message();
        message.setConversationId(event.getConversationId());
        message.setRole(Message.Role.assistant);
        message.setContent(event.getAnswer());
        message.setTokensUsed(event.getTokens() == null ? 0 : event.getTokens());
        message.setMetadata(JSON.toJSONString(buildMetadata(event)));
        return messageRepository.save(message);
    }

    private Map<String, Object> buildMetadata(AiReplyEvent event) {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("skill_used", event.getSkillUsed());
        metadata.put("sources", event.getSources() == null ? List.of() : event.getSources());
        metadata.put("book_labels", event.getBookLabels() == null ? List.of() : event.getBookLabels());
        metadata.put("confidence", event.getConfidence());
        metadata.put("audit_notes", event.getAuditNotes() == null ? List.of() : event.getAuditNotes());
        metadata.put("success", event.getSuccess());
        metadata.put("error_message", event.getErrorMessage());
        return metadata;
    }

    private void archiveToMongo(AiReplyEvent event) {
        ChatMessageArchive userArchive = ChatMessageArchive.builder()
                .eventId(event.getEventId())
                .requestId(event.getRequestId())
                .traceId(event.getTraceId())
                .conversationId(event.getConversationId())
                .userId(event.getUserId())
                .role("user")
                .content(event.getUserMessage())
                .timestamp(event.getTimestamp())
                .build();

        ChatMessageArchive assistantArchive = ChatMessageArchive.builder()
                .eventId(event.getEventId())
                .requestId(event.getRequestId())
                .traceId(event.getTraceId())
                .conversationId(event.getConversationId())
                .userId(event.getUserId())
                .role("assistant")
                .content(event.getAnswer())
                .tokensUsed(event.getTokens())
                .metadata(JSON.toJSONString(buildMetadata(event)))
                .timestamp(event.getTimestamp())
                .build();

        mongoArchiveService.archiveBatch(List.of(userArchive, assistantArchive));
    }

    private ChatMessageResponse toResponse(Message aiMessage, AiReplyEvent event) {
        LocalDateTime timestamp = aiMessage.getCreatedAt();
        if (timestamp == null && event.getTimestamp() != null) {
            timestamp = LocalDateTime.ofInstant(Instant.ofEpochMilli(event.getTimestamp()), ZoneId.systemDefault());
        }
        if (timestamp == null) {
            timestamp = LocalDateTime.now();
        }

        return ChatMessageResponse.builder()
                .messageId(aiMessage.getId())
                .conversationId(aiMessage.getConversationId())
                .content(aiMessage.getContent())
                .role("assistant")
                .timestamp(timestamp)
                .tokens(aiMessage.getTokensUsed())
                .skillUsed(event.getSkillUsed())
                .sources(event.getSources() == null ? List.of() : event.getSources())
                .explorationTasks(event.getExplorationTasks() == null ? List.of() : event.getExplorationTasks())
                .bookLabels(event.getBookLabels() == null ? List.of() : event.getBookLabels())
                .confidence(event.getConfidence())
                .auditNotes(event.getAuditNotes() == null ? List.of() : event.getAuditNotes())
                .build();
    }
}
