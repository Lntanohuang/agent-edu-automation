package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
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
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final RestTemplate restTemplate = new RestTemplate();
    private static final int HISTORY_LIMIT = 20;
    private static final int MAX_HISTORY_TOKENS = 512;

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    /**
     * 同步发送消息并获取 AI 回复
     */
    @Transactional
    public ChatMessageResponse sendMessage(Long userId, ChatMessageRequest request) {
        ConversationContext context = resolveConversationContext(userId, request);
        Conversation conversation = context.conversation();

        saveUserMessage(conversation.getId(), request.getMessage());
        conversationRepository.incrementMessageCount(conversation.getId());

        AiServiceReply aiReply = callAiService(request.getMessage(), conversation.getId(), context.historyMessages());

        Message aiMessage = saveAssistantMessage(conversation.getId(), aiReply);
        conversationRepository.incrementMessageCount(conversation.getId());

        return toResponse(aiMessage, aiReply);
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
    }

    /**
     * 同步调用 AI 服务
     */
    private AiServiceReply callAiService(String message, Long conversationId, List<Message> historyMessages) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity =
                    new HttpEntity<>(buildAiRequestBody(message, conversationId, historyMessages), headers);
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + "/rag/agent/chat",
                    entity,
                    String.class
            );

            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                throw new BusinessException(503, "AI 服务响应异常");
            }

            JSONObject obj = JSON.parseObject(response.getBody());
            if (obj == null) {
                throw new BusinessException(503, "AI 服务返回为空");
            }

            Boolean success = obj.getBoolean("success");
            if (Boolean.FALSE.equals(success)) {
                String error = obj.getString("error");
                String messageText = obj.getString("message");
                throw new BusinessException(503, "AI 服务失败: " + (error != null ? error : messageText));
            }

            String answer = obj.getString("answer") == null ? "" : obj.getString("answer").trim();
            if (answer.isEmpty()) {
                throw new BusinessException(503, "AI 服务返回空内容");
            }

            return new AiServiceReply(
                    answer,
                    obj.getString("skill_used"),
                    toStringList(obj.getJSONArray("sources")),
                    toStringList(obj.getJSONArray("exploration_tasks")),
                    toStringList(obj.getJSONArray("book_labels")),
                    obj.getString("confidence"),
                    toStringList(obj.getJSONArray("audit_notes"))
            );
        } catch (Exception e) {
            log.error("调用 AI 服务失败", e);
            if (e instanceof BusinessException businessException) {
                throw businessException;
            }
            throw new BusinessException(503, "AI 服务暂时不可用，请稍后再试");
        }
    }

    private ConversationContext resolveConversationContext(Long userId, ChatMessageRequest request) {
        Conversation conversation;
        List<Message> historyMessages = List.of();

        if (request.getConversationId() != null) {
            conversation = conversationRepository.findById(request.getConversationId())
                    .orElseThrow(() -> new BusinessException(404, "对话不存在"));
            if (!conversation.getUserId().equals(userId)) {
                throw new BusinessException(403, "无权访问该对话");
            }
            historyMessages = messageRepository.findRecentMessages(conversation.getId(), HISTORY_LIMIT);
        } else {
            conversation = new Conversation();
            conversation.setUserId(userId);
            conversation.setTitle(generateTitle(request.getMessage()));
            conversation.setContext(request.getContext() != null ? JSON.toJSONString(request.getContext()) : null);
            conversation.setStatus(Conversation.Status.active);
            conversationRepository.save(conversation);
        }

        return new ConversationContext(conversation, historyMessages);
    }

    private void saveUserMessage(Long conversationId, String content) {
        Message userMessage = new Message();
        userMessage.setConversationId(conversationId);
        userMessage.setRole(Message.Role.user);
        userMessage.setContent(content);
        messageRepository.save(userMessage);
    }

    private Message saveAssistantMessage(Long conversationId, AiServiceReply aiReply) {
        if (aiReply.answer() == null || aiReply.answer().trim().isEmpty()) {
            throw new BusinessException(503, "AI 返回空内容，未写入会话");
        }
        Message aiMessage = new Message();
        aiMessage.setConversationId(conversationId);
        aiMessage.setRole(Message.Role.assistant);
        aiMessage.setContent(aiReply.answer());
        aiMessage.setTokensUsed(aiReply.answer() == null ? 0 : aiReply.answer().length() / 2);
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("skill_used", aiReply.skillUsed());
        metadata.put("sources", aiReply.sources());
        metadata.put("book_labels", aiReply.bookLabels());
        metadata.put("confidence", aiReply.confidence());
        metadata.put("audit_notes", aiReply.auditNotes());
        aiMessage.setMetadata(JSON.toJSONString(metadata));
        return messageRepository.save(aiMessage);
    }

    private ChatMessageResponse toResponse(Message aiMessage, AiServiceReply aiReply) {
        return ChatMessageResponse.builder()
                .messageId(aiMessage.getId())
                .conversationId(aiMessage.getConversationId())
                .content(aiReply.answer())
                .role("assistant")
                .timestamp(aiMessage.getCreatedAt())
                .tokens(aiMessage.getTokensUsed())
                .skillUsed(aiReply.skillUsed())
                .sources(aiReply.sources())
                .explorationTasks(aiReply.explorationTasks())
                .bookLabels(aiReply.bookLabels())
                .confidence(aiReply.confidence())
                .auditNotes(aiReply.auditNotes())
                .build();
    }

    private Map<String, Object> buildAiRequestBody(String message, Long conversationId, List<Message> historyMessages) {
        List<Map<String, String>> history = historyMessages.stream()
                .map(msg -> Map.of(
                        "role", msg.getRole() == Message.Role.assistant ? "assistant" : "user",
                        "content", msg.getContent()
                ))
                .toList();
        Map<String, Object> body = new HashMap<>();
        body.put("query", message);
        body.put("conversation_id", String.valueOf(conversationId));
        body.put("history", history);
        body.put("max_history_tokens", MAX_HISTORY_TOKENS);
        return body;
    }

    private List<String> toStringList(JSONArray array) {
        if (array == null || array.isEmpty()) {
            return List.of();
        }
        return array.stream().map(String::valueOf).toList();
    }

    private String generateTitle(String message) {
        if (message.length() <= 20) {
            return message;
        }
        return message.substring(0, 20) + "...";
    }

    private record ConversationContext(Conversation conversation, List<Message> historyMessages) {}

    private record AiServiceReply(
            String answer,
            String skillUsed,
            List<String> sources,
            List<String> explorationTasks,
            List<String> bookLabels,
            String confidence,
            List<String> auditNotes
    ) {}
}
