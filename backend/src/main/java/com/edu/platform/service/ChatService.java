package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.edu.platform.chat.event.UserChatMessageEvent;
import com.edu.platform.chat.service.ChatContextCacheService;
import com.edu.platform.chat.service.ChatEventPublisher;
import com.edu.platform.chat.service.ChatPendingReplyRegistry;
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
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final ChatEventPublisher chatEventPublisher;
    private final ChatPendingReplyRegistry pendingReplyRegistry;
    private final ChatContextCacheService cacheService;

    @Value("${chat.reply.timeout-ms:60000}")
    private long replyTimeoutMs;

    /**
     * 发送消息：
     * 1. API 层只校验会话并投递用户消息事件
     * 2. 由 MQ 消费者异步调模型并落库
     * 3. 同步等待一段时间以兼容现有前端请求-响应模式
     */
    @Transactional
    public ChatMessageResponse sendMessage(Long userId, ChatMessageRequest request) {
        Conversation conversation = resolveConversation(userId, request);
        UserChatMessageEvent event = buildEvent(userId, conversation.getId(), request);

        CompletableFuture<ChatMessageResponse> pendingReply = pendingReplyRegistry.register(event.getRequestId());
        try {
            chatEventPublisher.publishUserMessage(event);
            return pendingReply.get(replyTimeoutMs, TimeUnit.MILLISECONDS);
        } catch (TimeoutException timeoutException) {
            log.warn("等待 AI 回复超时: requestId={}, conversationId={}",
                    event.getRequestId(), conversation.getId());
            return buildPendingResponse(conversation.getId());
        } catch (InterruptedException interruptedException) {
            Thread.currentThread().interrupt();
            throw new BusinessException(500, "请求处理中断，请重试");
        } catch (ExecutionException executionException) {
            Throwable cause = executionException.getCause();
            if (cause instanceof BusinessException businessException) {
                throw businessException;
            }
            log.error("异步回复处理失败: requestId={}", event.getRequestId(), executionException);
            throw new BusinessException(503, "AI 服务暂时不可用，请稍后再试");
        } finally {
            pendingReplyRegistry.cleanup(event.getRequestId());
        }
    }

    /**
     * 获取对话列表
     */
    public Page<ConversationDTO> getConversations(Long userId, Pageable pageable) {
        Page<Conversation> conversations = conversationRepository.findByUserIdOrderByUpdatedAtDesc(userId, pageable);

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

        return new PageImpl<>(dtoList, pageable, conversations.getTotalElements());
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

    private UserChatMessageEvent buildEvent(Long userId, Long conversationId, ChatMessageRequest request) {
        return UserChatMessageEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .requestId(UUID.randomUUID().toString())
                .traceId(UUID.randomUUID().toString())
                .conversationId(conversationId)
                .userId(userId)
                .message(request.getMessage())
                .context(request.getContext() == null ? Map.of() : request.getContext())
                .timestamp(System.currentTimeMillis())
                .build();
    }

    private ChatMessageResponse buildPendingResponse(Long conversationId) {
        return ChatMessageResponse.builder()
                .conversationId(conversationId)
                .role("assistant")
                .content("消息已接收，正在生成中，请稍后刷新会话查看结果。")
                .timestamp(LocalDateTime.now())
                .tokens(0)
                .sources(List.of())
                .explorationTasks(List.of())
                .bookLabels(List.of())
                .auditNotes(List.of())
                .build();
    }

    private String generateTitle(String message) {
        if (message.length() <= 20) {
            return message;
        }
        return message.substring(0, 20) + "...";
    }
}
