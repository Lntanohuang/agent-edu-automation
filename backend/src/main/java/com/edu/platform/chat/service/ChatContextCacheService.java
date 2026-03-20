package com.edu.platform.chat.service;

import com.alibaba.fastjson2.JSON;
import com.edu.platform.entity.Message;
import com.edu.platform.repository.MessageRepository;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ChatContextCacheService {

    private static final String HISTORY_KEY_FORMAT = "chat:session:%d:messages";
    private static final String META_KEY_FORMAT = "chat:session:%d:meta";
    private static final String DIGEST_KEY_FORMAT = "chat:msg:digest:%s";

    private final StringRedisTemplate redisTemplate;
    private final MessageRepository messageRepository;

    @Value("${chat.context.history-window:40}")
    private int historyWindow;

    @Value("${chat.context.ttl-days:30}")
    private int ttlDays;

    public List<HistoryMessage> loadHistory(Long conversationId, int limit) {
        String key = historyKey(conversationId);
        int safeLimit = Math.max(1, Math.min(limit, historyWindow));

        List<String> cached = redisTemplate.opsForList().range(key, -safeLimit, -1);
        if (cached != null && !cached.isEmpty()) {
            return parseHistory(cached);
        }

        List<Message> dbMessages = messageRepository.findRecentMessages(conversationId, safeLimit);
        if (dbMessages.isEmpty()) {
            return List.of();
        }

        Collections.reverse(dbMessages);
        List<String> serialized = dbMessages.stream()
                .map(this::fromEntity)
                .map(JSON::toJSONString)
                .toList();

        redisTemplate.opsForList().rightPushAll(key, serialized);
        trimHistory(key);
        touchConversation(conversationId);

        return parseHistory(serialized);
    }

    public void appendUserMessage(Long conversationId, String content) {
        appendMessage(conversationId, new HistoryMessage("user", content, null, System.currentTimeMillis()));
    }

    public void appendAssistantMessage(Long conversationId, String content, Integer tokens) {
        appendMessage(conversationId, new HistoryMessage("assistant", content, tokens, System.currentTimeMillis()));
    }

    public boolean markEventProcessed(String digestId) {
        String key = String.format(DIGEST_KEY_FORMAT, digestId);
        Boolean created = redisTemplate.opsForValue().setIfAbsent(key, "1", Duration.ofDays(ttlDays));
        return Boolean.TRUE.equals(created);
    }

    public void clearEventDigest(String digestId) {
        redisTemplate.delete(String.format(DIGEST_KEY_FORMAT, digestId));
    }

    public void clearConversation(Long conversationId) {
        redisTemplate.delete(historyKey(conversationId));
        redisTemplate.delete(metaKey(conversationId));
    }

    private void appendMessage(Long conversationId, HistoryMessage message) {
        String key = historyKey(conversationId);
        redisTemplate.opsForList().rightPush(key, JSON.toJSONString(message));
        trimHistory(key);
        touchConversation(conversationId);
    }

    private void trimHistory(String key) {
        int safeWindow = Math.max(1, historyWindow);
        redisTemplate.opsForList().trim(key, -safeWindow, -1);
    }

    private void touchConversation(Long conversationId) {
        String historyKey = historyKey(conversationId);
        String metaKey = metaKey(conversationId);
        Duration ttl = Duration.ofDays(Math.max(1, ttlDays));
        redisTemplate.expire(historyKey, ttl);
        redisTemplate.opsForHash().put(metaKey, "last_active_at", String.valueOf(System.currentTimeMillis()));
        redisTemplate.expire(metaKey, ttl);
    }

    private List<HistoryMessage> parseHistory(List<String> data) {
        List<HistoryMessage> result = new ArrayList<>();
        for (String item : data) {
            if (item == null || item.isBlank()) {
                continue;
            }
            HistoryMessage message = JSON.parseObject(item, HistoryMessage.class);
            if (message != null && message.getContent() != null) {
                result.add(message);
            }
        }
        return result;
    }

    private HistoryMessage fromEntity(Message message) {
        return new HistoryMessage(
                message.getRole() == Message.Role.assistant ? "assistant" : "user",
                message.getContent(),
                message.getTokensUsed(),
                message.getCreatedAt() == null ? System.currentTimeMillis() : message.getCreatedAt().atZone(java.time.ZoneId.systemDefault()).toInstant().toEpochMilli()
        );
    }

    private String historyKey(Long conversationId) {
        return String.format(HISTORY_KEY_FORMAT, conversationId);
    }

    private String metaKey(Long conversationId) {
        return String.format(META_KEY_FORMAT, conversationId);
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HistoryMessage {
        private String role;
        private String content;
        private Integer tokens;
        private Long timestamp;
    }
}
