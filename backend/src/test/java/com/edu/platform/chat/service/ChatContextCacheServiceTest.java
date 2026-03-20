package com.edu.platform.chat.service;

import com.alibaba.fastjson2.JSON;
import com.edu.platform.chat.BaseUnitTest;
import com.edu.platform.entity.Message;
import com.edu.platform.repository.MessageRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.ListOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.mockito.Mockito.lenient;

@DisplayName("ChatContextCacheService 单元测试")
class ChatContextCacheServiceTest extends BaseUnitTest {

    @Mock
    private StringRedisTemplate redisTemplate;
    @Mock
    private MessageRepository messageRepository;
    @Mock
    private ListOperations<String, String> listOps;
    @Mock
    private ValueOperations<String, String> valueOps;
    @Mock
    private HashOperations<String, Object, Object> hashOps;

    @InjectMocks
    private ChatContextCacheService cacheService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(cacheService, "historyWindow", 10);
        ReflectionTestUtils.setField(cacheService, "ttlDays", 30);
        lenient().when(redisTemplate.opsForList()).thenReturn(listOps);
        lenient().when(redisTemplate.opsForValue()).thenReturn(valueOps);
        lenient().when(redisTemplate.opsForHash()).thenReturn(hashOps);
    }

    // ========== loadHistory ==========

    @Test
    @DisplayName("缓存命中时直接返回，不查 DB")
    void loadHistory_whenCacheHit_returnsFromRedis() {
        ChatContextCacheService.HistoryMessage msg = new ChatContextCacheService.HistoryMessage("user", "你好", null, 1000L);
        when(listOps.range("chat:session:1:messages", -5, -1))
                .thenReturn(List.of(JSON.toJSONString(msg)));

        List<ChatContextCacheService.HistoryMessage> result = cacheService.loadHistory(1L, 5);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getContent()).isEqualTo("你好");
        verify(messageRepository, never()).findRecentMessages(anyLong(), anyInt());
    }

    @Test
    @DisplayName("缓存未命中时查 DB 并回填 Redis")
    void loadHistory_whenCacheMiss_queriesDbAndPopulatesRedis() {
        when(listOps.range(anyString(), anyLong(), anyLong())).thenReturn(List.of());

        Message dbMsg = new Message();
        dbMsg.setConversationId(1L);
        dbMsg.setRole(Message.Role.user);
        dbMsg.setContent("数据库消息");
        dbMsg.setCreatedAt(LocalDateTime.now());
        when(messageRepository.findRecentMessages(1L, 5)).thenReturn(List.of(dbMsg));

        List<ChatContextCacheService.HistoryMessage> result = cacheService.loadHistory(1L, 5);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getContent()).isEqualTo("数据库消息");
        verify(listOps).rightPushAll(eq("chat:session:1:messages"), anyList());
    }

    @Test
    @DisplayName("DB 也为空时返回空列表")
    void loadHistory_whenDbAlsoEmpty_returnsEmptyList() {
        when(listOps.range(anyString(), anyLong(), anyLong())).thenReturn(List.of());
        when(messageRepository.findRecentMessages(1L, 5)).thenReturn(List.of());

        List<ChatContextCacheService.HistoryMessage> result = cacheService.loadHistory(1L, 5);

        assertThat(result).isEmpty();
        verify(listOps, never()).rightPushAll(anyString(), anyList());
    }

    @Test
    @DisplayName("limit 不超过 historyWindow")
    void loadHistory_respectsHistoryWindow() {
        when(listOps.range(anyString(), anyLong(), anyLong())).thenReturn(List.of());
        when(messageRepository.findRecentMessages(eq(1L), eq(10))).thenReturn(List.of());

        cacheService.loadHistory(1L, 999);

        // historyWindow=10, 所以 safeLimit=10
        verify(messageRepository).findRecentMessages(1L, 10);
    }

    @Test
    @DisplayName("缓存中的 null/空字符串被过滤")
    void loadHistory_skipsNullAndBlankEntries() {
        ChatContextCacheService.HistoryMessage msg = new ChatContextCacheService.HistoryMessage("user", "有效消息", null, 1000L);
        when(listOps.range(anyString(), anyLong(), anyLong()))
                .thenReturn(List.of("", "  ", JSON.toJSONString(msg)));

        List<ChatContextCacheService.HistoryMessage> result = cacheService.loadHistory(1L, 5);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getContent()).isEqualTo("有效消息");
    }

    // ========== appendMessage ==========

    @Test
    @DisplayName("追加用户消息到 Redis 并 trim")
    void appendUserMessage_pushesAndTrims() {
        cacheService.appendUserMessage(1L, "你好");

        verify(listOps).rightPush(eq("chat:session:1:messages"), argThat(json ->
                json.contains("\"role\":\"user\"") && json.contains("你好")));
        verify(listOps).trim("chat:session:1:messages", -10, -1);
    }

    @Test
    @DisplayName("追加助手消息包含 tokens 字段")
    void appendAssistantMessage_includesTokens() {
        cacheService.appendAssistantMessage(1L, "回答内容", 50);

        verify(listOps).rightPush(eq("chat:session:1:messages"), argThat(json ->
                json.contains("\"role\":\"assistant\"") && json.contains("\"tokens\":50")));
    }

    // ========== markEventProcessed / clearEventDigest ==========

    @Test
    @DisplayName("幂等 key 不存在时返回 true")
    void markEventProcessed_whenKeyAbsent_returnsTrue() {
        when(valueOps.setIfAbsent(anyString(), anyString(), any(Duration.class))).thenReturn(true);

        assertThat(cacheService.markEventProcessed("evt-001")).isTrue();
        verify(valueOps).setIfAbsent("chat:msg:digest:evt-001", "1", Duration.ofDays(30));
    }

    @Test
    @DisplayName("幂等 key 已存在时返回 false（重复事件）")
    void markEventProcessed_whenKeyPresent_returnsFalse() {
        when(valueOps.setIfAbsent(anyString(), anyString(), any(Duration.class))).thenReturn(false);

        assertThat(cacheService.markEventProcessed("evt-001")).isFalse();
    }

    @Test
    @DisplayName("clearEventDigest 删除正确的 key")
    void clearEventDigest_deletesCorrectKey() {
        cacheService.clearEventDigest("evt-001");

        verify(redisTemplate).delete("chat:msg:digest:evt-001");
    }

    // ========== clearConversation ==========

    @Test
    @DisplayName("清空会话删除 history 和 meta 两个 key")
    void clearConversation_deletesBothKeys() {
        cacheService.clearConversation(1L);

        verify(redisTemplate).delete("chat:session:1:messages");
        verify(redisTemplate).delete("chat:session:1:meta");
    }

    // ========== touchConversation（间接测试） ==========

    @Test
    @DisplayName("追加消息后设置 TTL 和 meta hash")
    void appendMessage_touchesConversation() {
        cacheService.appendUserMessage(1L, "测试");

        verify(redisTemplate).expire("chat:session:1:messages", Duration.ofDays(30));
        verify(hashOps).put(eq("chat:session:1:meta"), eq("last_active_at"), anyString());
        verify(redisTemplate).expire("chat:session:1:meta", Duration.ofDays(30));
    }
}
