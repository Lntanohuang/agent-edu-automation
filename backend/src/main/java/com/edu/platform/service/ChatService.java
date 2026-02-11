package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.edu.platform.common.BusinessException;
import com.edu.platform.dto.*;
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

import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    /**
     * 发送消息并获取 AI 回复
     */
    @Transactional
    public ChatMessageResponse sendMessage(Long userId, ChatMessageRequest request) {
        Conversation conversation;

        // 确定对话
        if (request.getConversationId() != null) {
            conversation = conversationRepository.findById(request.getConversationId())
                    .orElseThrow(() -> new BusinessException(404, "对话不存在"));
            
            if (!conversation.getUserId().equals(userId)) {
                throw new BusinessException(403, "无权访问该对话");
            }
        } else {
            // 创建新对话
            conversation = new Conversation();
            conversation.setUserId(userId);
            conversation.setTitle(generateTitle(request.getMessage()));
            conversation.setContext(request.getContext() != null ? JSON.toJSONString(request.getContext()) : null);
            conversation.setStatus(Conversation.Status.active);
            conversationRepository.save(conversation);
        }

        // 保存用户消息
        Message userMessage = new Message();
        userMessage.setConversationId(conversation.getId());
        userMessage.setRole(Message.Role.user);
        userMessage.setContent(request.getMessage());
        messageRepository.save(userMessage);

        // 增加消息计数
        conversationRepository.incrementMessageCount(conversation.getId());

        // 调用 AI 服务获取回复
        String aiReply = callAiService(request.getMessage(), conversation.getId());

        // 保存 AI 回复
        Message aiMessage = new Message();
        aiMessage.setConversationId(conversation.getId());
        aiMessage.setRole(Message.Role.assistant);
        aiMessage.setContent(aiReply);
        aiMessage.setTokensUsed(aiReply.length() / 2);  // 粗略估计
        messageRepository.save(aiMessage);

        // 增加消息计数
        conversationRepository.incrementMessageCount(conversation.getId());

        return ChatMessageResponse.builder()
                .messageId(aiMessage.getId())
                .conversationId(conversation.getId())
                .content(aiReply)
                .role("assistant")
                .timestamp(aiMessage.getCreatedAt())
                .tokens(aiMessage.getTokensUsed())
                .build();
    }

    /**
     * 调用 AI 服务
     * TODO: 实际项目中应该调用 Python AI 服务
     */
    private String callAiService(String message, Long conversationId) {
        try {
            // 模拟调用 AI 服务
            // 实际项目中应该是:
            // HttpHeaders headers = new HttpHeaders();
            // headers.setContentType(MediaType.APPLICATION_JSON);
            // Map<String, Object> body = new HashMap<>();
            // body.put("messages", buildMessages(message, conversationId));
            // HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            // ResponseEntity<Map> response = restTemplate.postForEntity(
            //     aiServiceUrl + "/chat/completions", entity, Map.class);
            // return extractContent(response.getBody());

            // 模拟延迟
            Thread.sleep(500);
            
            return generateMockReply(message);
        } catch (Exception e) {
            log.error("调用 AI 服务失败", e);
            throw new BusinessException("AI 服务暂时不可用，请稍后再试");
        }
    }

    /**
     * 生成模拟回复（用于测试）
     */
    private String generateMockReply(String message) {
        String[] replies = {
            "这是一个很好的教学问题！我建议您可以从以下几个方面考虑：\n\n1. **明确教学目标** - 确保学生理解核心概念\n2. **设计互动环节** - 增加学生参与度\n3. **使用多媒体资源** - 丰富教学内容\n4. **及时反馈** - 帮助学生巩固知识",
            
            "根据您的需求，我为您提供以下建议：\n\n- 采用**启发式教学**方法\n- 设计**分层教学**活动\n- 运用**项目式学习**模式\n- 结合**翻转课堂**理念\n\n这些方法可以有效提升教学效果。",
            
            "我理解您的困惑。针对这个问题，您可以尝试：\n\n### 1. 课前准备\n- 深入了解学生学情\n- 准备充足的教学素材\n\n### 2. 课堂实施\n- 创设真实情境\n- 引导自主探究\n\n### 3. 课后反思\n- 收集学生反馈\n- 持续改进教学"
        };
        return replies[(int) (Math.random() * replies.length)];
    }

    /**
     * 获取对话列表
     */
    public Page<ConversationDTO> getConversations(Long userId, Pageable pageable) {
        Page<Conversation> conversations = conversationRepository.findByUserIdOrderByUpdatedAtDesc(userId, pageable);
        
        List<ConversationDTO> dtoList = conversations.getContent().stream()
                .map(conv -> {
                    // 获取最后一条消息
                    List<Message> messages = messageRepository.findByConversationIdOrderByCreatedAtAsc(conv.getId());
                    String lastMessage = messages.isEmpty() ? "" : 
                            messages.get(messages.size() - 1).getContent();
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

        // 先删除消息
        messageRepository.deleteByConversationId(conversationId);
        // 再删除对话
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
     * 生成对话标题（取前 20 个字符）
     */
    private String generateTitle(String message) {
        if (message.length() <= 20) {
            return message;
        }
        return message.substring(0, 20) + "...";
    }
}
