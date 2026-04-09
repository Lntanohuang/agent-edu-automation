package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.mongo.ChatMessageArchive;
import com.edu.platform.chat.service.AiModelClient;
import com.edu.platform.chat.service.ChatContextCacheService;
import com.edu.platform.chat.service.ChatMongoArchiveService;
import com.edu.platform.common.BusinessException;
import com.edu.platform.dto.ChatMessageRequest;
import com.edu.platform.dto.ChatMessageResponse;
import com.edu.platform.dto.ConversationDTO;
import com.edu.platform.entity.Conversation;
import com.edu.platform.entity.Message;
import com.edu.platform.repository.ConversationRepository;
import com.edu.platform.repository.MessageRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final ChatContextCacheService cacheService;
    private final AiModelClient aiModelClient;
    private final ChatMongoArchiveService mongoArchiveService;

    private static final int HISTORY_LIMIT = 20;

    /**
     * 发送消息（同步模式）：直接调用 AI 服务并持久化结果。
     */
    @Transactional
    public ChatMessageResponse sendMessage(Long userId, ChatMessageRequest request) {
        long startedAt = System.currentTimeMillis();
        String traceId = UUID.randomUUID().toString().replace("-", "");
        log.info(
                "[chat] step=received traceId={} userId={} incomingConversationId={} messageChars={}",
                traceId,
                userId,
                request.getConversationId(),
                request.getMessage() == null ? 0 : request.getMessage().length()
        );

        Conversation conversation = resolveConversation(userId, request);
        Long conversationId = conversation.getId();
        log.info(
                "[chat] step=conversation_resolved traceId={} conversationId={} createdNew={}",
                traceId,
                conversationId,
                request.getConversationId() == null
        );

        List<ChatContextCacheService.HistoryMessage> history =
                cacheService.loadHistory(conversationId, HISTORY_LIMIT);
        log.info(
                "[chat] step=history_loaded traceId={} conversationId={} historyCount={}",
                traceId,
                conversationId,
                history.size()
        );

        AiModelClient.AiServiceReply aiReply;
        long aiStartedAt = System.currentTimeMillis();
        try {
            aiReply = aiModelClient.generateReplyWithTrace(request.getMessage(), conversationId, history, traceId);
            log.info(
                    "[chat] step=ai_reply_received traceId={} conversationId={} elapsedMs={} skillUsed={} confidence={} sourceCount={} taskCount={}",
                    traceId,
                    conversationId,
                    System.currentTimeMillis() - aiStartedAt,
                    aiReply.skillUsed(),
                    aiReply.confidence(),
                    aiReply.sources() == null ? 0 : aiReply.sources().size(),
                    aiReply.explorationTasks() == null ? 0 : aiReply.explorationTasks().size()
            );
        } catch (BusinessException e) {
            log.warn(
                    "[chat] step=ai_reply_failed traceId={} conversationId={} elapsedMs={} message={}",
                    traceId,
                    conversationId,
                    System.currentTimeMillis() - aiStartedAt,
                    e.getMessage()
            );
            throw e;
        } catch (Exception e) {
            log.error("[chat] step=ai_reply_error traceId={} conversationId={}", traceId, conversationId, e);
            throw new BusinessException(503, "AI 服务暂时不可用，请稍后再试");
        }

        // 持久化用户消息
        Message userMessage = new Message();
        userMessage.setConversationId(conversationId);
        userMessage.setRole(Message.Role.user);
        userMessage.setContent(request.getMessage());
        messageRepository.save(userMessage);
        log.info(
                "[chat] step=user_message_persisted traceId={} conversationId={} userMessageId={}",
                traceId,
                conversationId,
                userMessage.getId()
        );

        // 持久化 AI 回复
        int tokens = aiReply.answer() == null ? 0 : aiReply.answer().length() / 2;
        Message aiMessage = new Message();
        aiMessage.setConversationId(conversationId);
        aiMessage.setRole(Message.Role.assistant);
        aiMessage.setContent(aiReply.answer());
        aiMessage.setTokensUsed(tokens);
        aiMessage.setMetadata(JSON.toJSONString(buildMetadata(aiReply)));
        messageRepository.save(aiMessage);
        log.info(
                "[chat] step=assistant_message_persisted traceId={} conversationId={} aiMessageId={} tokens={}",
                traceId,
                conversationId,
                aiMessage.getId(),
                tokens
        );

        // 更新会话消息计数
        conversationRepository.incrementMessageCount(conversationId);
        conversationRepository.incrementMessageCount(conversationId);
        log.info("[chat] step=conversation_counter_updated traceId={} conversationId={}", traceId, conversationId);

        // 更新 Redis 缓存
        cacheService.appendUserMessage(conversationId, request.getMessage());
        cacheService.appendAssistantMessage(conversationId, aiReply.answer(), tokens);
        log.info("[chat] step=history_cache_updated traceId={} conversationId={}", traceId, conversationId);

        // 异步归档到 MongoDB
        archiveToMongo(userId, conversationId, request.getMessage(), aiReply);
        log.info("[chat] step=mongo_archive_written traceId={} conversationId={}", traceId, conversationId);

        log.info(
                "[chat] step=completed traceId={} conversationId={} totalElapsedMs={}",
                traceId,
                conversationId,
                System.currentTimeMillis() - startedAt
        );

        return ChatMessageResponse.builder()
                .messageId(aiMessage.getId())
                .conversationId(conversationId)
                .content(aiReply.answer())
                .role("assistant")
                .timestamp(aiMessage.getCreatedAt() != null ? aiMessage.getCreatedAt() : LocalDateTime.now())
                .tokens(tokens)
                .skillUsed(aiReply.skillUsed())
                .sources(aiReply.sources() == null ? List.of() : aiReply.sources())
                .explorationTasks(aiReply.explorationTasks() == null ? List.of() : aiReply.explorationTasks())
                .bookLabels(aiReply.bookLabels() == null ? List.of() : aiReply.bookLabels())
                .confidence(aiReply.confidence())
                .auditNotes(aiReply.auditNotes() == null ? List.of() : aiReply.auditNotes())
                .build();
    }

    /**
     * 获取对话列表
     */
    public org.springframework.data.domain.Page<ConversationDTO> getConversations(Long userId, org.springframework.data.domain.Pageable pageable) {
        var conversations = conversationRepository.findByUserIdOrderByUpdatedAtDesc(userId, pageable);

        List<ConversationDTO> dtoList = conversations.getContent().stream()
                .map(conv -> {
                    List<Message> messages = messageRepository.findByConversationIdOrderByCreatedAtAsc(conv.getId());
                    String lastMessage = messages.isEmpty() ? "" : messages.get(messages.size() - 1).getContent();
                    if (lastMessage.length() > 50) {
                        lastMessage = lastMessage.substring(0, 50) + "...";
                    }
                    return ConversationDTO.fromEntity(conv, lastMessage);
                })
                .toList();

        return new org.springframework.data.domain.PageImpl<>(dtoList, pageable, conversations.getTotalElements());
    }

    /**
     * 获取对话消息历史
     */
    public List<ChatMessageResponse> getMessages(Long userId, Long conversationId) {
        Conversation conversation = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new BusinessException(404, "对话不存在"));

        if (!conversation.getUserId().equals(userId)) {
            throw new BusinessException(403, "无权访问该对话");
        }

        List<Message> messages = messageRepository.findByConversationIdOrderByCreatedAtAsc(conversationId);

        return messages.stream()
                .map(msg -> ChatMessageResponse.builder()
                        .messageId(msg.getId())
                        .conversationId(msg.getConversationId())
                        .content(msg.getContent())
                        .role(msg.getRole().name())
                        .timestamp(msg.getCreatedAt())
                        .tokens(msg.getTokensUsed())
                        .build())
                .toList();
    }

    /**
     * 删除对话
     */
    @Transactional
    public void deleteConversation(Long userId, Long conversationId) {
        Conversation conversation = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new BusinessException(404, "对话不存在"));

        if (!conversation.getUserId().equals(userId)) {
            throw new BusinessException(403, "无权删除该对话");
        }

        messageRepository.deleteByConversationId(conversationId);
        conversationRepository.deleteById(conversationId);
        cacheService.clearConversation(conversationId);
    }

    /**
     * 清空对话消息
     */
    @Transactional
    public void clearMessages(Long userId, Long conversationId) {
        Conversation conversation = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new BusinessException(404, "对话不存在"));

        if (!conversation.getUserId().equals(userId)) {
            throw new BusinessException(403, "无权操作该对话");
        }

        messageRepository.deleteByConversationId(conversationId);
        cacheService.clearConversation(conversationId);
    }

    private Conversation resolveConversation(Long userId, ChatMessageRequest request) {
        if (request.getConversationId() != null) {
            Conversation conversation = conversationRepository.findById(request.getConversationId())
                    .orElseThrow(() -> new BusinessException(404, "对话不存在"));
            if (!conversation.getUserId().equals(userId)) {
                throw new BusinessException(403, "无权访问该对话");
            }
            return conversation;
        }

        Conversation conversation = new Conversation();
        conversation.setUserId(userId);
        conversation.setTitle(generateTitle(request.getMessage()));
        conversation.setContext(request.getContext() != null ? JSON.toJSONString(request.getContext()) : null);
        conversation.setStatus(Conversation.Status.active);
        return conversationRepository.save(conversation);
    }

    private Map<String, Object> buildMetadata(AiModelClient.AiServiceReply reply) {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("skill_used", reply.skillUsed());
        metadata.put("sources", reply.sources() == null ? List.of() : reply.sources());
        metadata.put("book_labels", reply.bookLabels() == null ? List.of() : reply.bookLabels());
        metadata.put("confidence", reply.confidence());
        metadata.put("audit_notes", reply.auditNotes() == null ? List.of() : reply.auditNotes());
        return metadata;
    }

    private void archiveToMongo(Long userId, Long conversationId, String userMessage, AiModelClient.AiServiceReply reply) {
        ChatMessageArchive userArchive = ChatMessageArchive.builder()
                .conversationId(conversationId)
                .userId(userId)
                .role("user")
                .content(userMessage)
                .timestamp(System.currentTimeMillis())
                .build();

        ChatMessageArchive assistantArchive = ChatMessageArchive.builder()
                .conversationId(conversationId)
                .userId(userId)
                .role("assistant")
                .content(reply.answer())
                .metadata(JSON.toJSONString(buildMetadata(reply)))
                .timestamp(System.currentTimeMillis())
                .build();

        mongoArchiveService.archiveBatch(List.of(userArchive, assistantArchive));
    }

    private String generateTitle(String message) {
        if (message.length() <= 20) {
            return message;
        }
        return message.substring(0, 20) + "...";
    }
}
