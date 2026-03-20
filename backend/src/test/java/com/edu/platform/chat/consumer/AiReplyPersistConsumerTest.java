package com.edu.platform.chat.consumer;

import com.edu.platform.chat.BaseUnitTest;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.service.ChatContextCacheService;
import com.edu.platform.chat.service.ChatMongoArchiveService;
import com.edu.platform.chat.service.ChatPendingReplyRegistry;
import com.edu.platform.chat.service.ChatWebSocketNotifier;
import com.edu.platform.entity.Message;
import com.edu.platform.repository.ConversationRepository;
import com.edu.platform.repository.MessageRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@DisplayName("AiReplyPersistConsumer 单元测试")
class AiReplyPersistConsumerTest extends BaseUnitTest {

    @Mock private MessageRepository messageRepository;
    @Mock private ConversationRepository conversationRepository;
    @Mock private ChatContextCacheService cacheService;
    @Mock private ChatMongoArchiveService mongoArchiveService;
    @Mock private ChatPendingReplyRegistry pendingReplyRegistry;
    @Mock private ChatWebSocketNotifier webSocketNotifier;

    @InjectMocks
    private AiReplyPersistConsumer consumer;

    private AiReplyEvent buildEvent() {
        return AiReplyEvent.builder()
                .eventId("evt-1")
                .requestId("req-1")
                .traceId("trace-1")
                .conversationId(1L)
                .userId(100L)
                .userMessage("问题")
                .answer("回答内容")
                .tokens(10)
                .skillUsed("law_explain")
                .sources(List.of("教材P10"))
                .explorationTasks(List.of())
                .bookLabels(List.of("法理学"))
                .confidence("high")
                .auditNotes(List.of())
                .success(true)
                .timestamp(System.currentTimeMillis())
                .build();
    }

    @Test
    @DisplayName("event 为 null → 跳过")
    void consume_whenNull_doesNothing() {
        consumer.consume(null);
        verifyNoInteractions(messageRepository);
    }

    @Test
    @DisplayName("重复 event → 跳过持久化")
    void consume_whenDuplicate_skips() {
        when(cacheService.markEventProcessed("persist-consume:evt-1")).thenReturn(false);

        consumer.consume(buildEvent());

        verify(messageRepository, never()).save(any());
    }

    @Test
    @DisplayName("正常流程：保存 user 和 assistant 两条消息")
    void consume_happyPath_savesTwoMessages() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        Message savedMsg = new Message();
        savedMsg.setId(1L);
        savedMsg.setConversationId(1L);
        savedMsg.setContent("回答内容");
        savedMsg.setRole(Message.Role.assistant);
        savedMsg.setTokensUsed(10);
        when(messageRepository.save(any())).thenReturn(savedMsg);

        consumer.consume(buildEvent());

        ArgumentCaptor<Message> captor = ArgumentCaptor.forClass(Message.class);
        verify(messageRepository, times(2)).save(captor.capture());
        List<Message> saved = captor.getAllValues();
        assertThat(saved.get(0).getRole()).isEqualTo(Message.Role.user);
        assertThat(saved.get(1).getRole()).isEqualTo(Message.Role.assistant);
    }

    @Test
    @DisplayName("incrementMessageCount 调用两次")
    void consume_incrementsCountTwice() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        Message savedMsg = new Message();
        savedMsg.setId(1L);
        savedMsg.setConversationId(1L);
        savedMsg.setContent("回答");
        savedMsg.setTokensUsed(10);
        when(messageRepository.save(any())).thenReturn(savedMsg);

        consumer.consume(buildEvent());

        verify(conversationRepository, times(2)).incrementMessageCount(1L);
    }

    @Test
    @DisplayName("追加 user 和 assistant 消息到 Redis 缓存")
    void consume_appendsBothToRedisCache() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        Message savedMsg = new Message();
        savedMsg.setId(1L);
        savedMsg.setConversationId(1L);
        savedMsg.setContent("回答内容");
        savedMsg.setTokensUsed(10);
        when(messageRepository.save(any())).thenReturn(savedMsg);

        consumer.consume(buildEvent());

        verify(cacheService).appendUserMessage(1L, "问题");
        verify(cacheService).appendAssistantMessage(1L, "回答内容", 10);
    }

    @Test
    @DisplayName("归档到 MongoDB")
    void consume_archivesToMongo() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        Message savedMsg = new Message();
        savedMsg.setId(1L);
        savedMsg.setConversationId(1L);
        savedMsg.setContent("回答");
        savedMsg.setTokensUsed(10);
        when(messageRepository.save(any())).thenReturn(savedMsg);

        consumer.consume(buildEvent());

        verify(mongoArchiveService).archiveBatch(argThat(list -> list.size() == 2));
    }

    @Test
    @DisplayName("complete CompletableFuture")
    void consume_completesReplyFuture() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        Message savedMsg = new Message();
        savedMsg.setId(1L);
        savedMsg.setConversationId(1L);
        savedMsg.setContent("回答内容");
        savedMsg.setTokensUsed(10);
        when(messageRepository.save(any())).thenReturn(savedMsg);

        consumer.consume(buildEvent());

        verify(pendingReplyRegistry).complete(eq("req-1"), argThat(resp ->
                "回答内容".equals(resp.getContent())));
    }

    @Test
    @DisplayName("推送管理员 WebSocket")
    void consume_pushesToAdmin() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        Message savedMsg = new Message();
        savedMsg.setId(1L);
        savedMsg.setConversationId(1L);
        savedMsg.setContent("回答");
        savedMsg.setTokensUsed(10);
        when(messageRepository.save(any())).thenReturn(savedMsg);

        consumer.consume(buildEvent());

        verify(webSocketNotifier).pushToAdmin(any());
    }

    @Test
    @DisplayName("持久化失败 → 清除幂等 key + completeExceptionally")
    void consume_whenSaveFails_clearsDigestAndFails() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        when(messageRepository.save(any())).thenThrow(new RuntimeException("DB 异常"));

        assertThatThrownBy(() -> consumer.consume(buildEvent()))
                .isInstanceOf(RuntimeException.class);

        verify(cacheService).clearEventDigest("persist-consume:evt-1");
        verify(pendingReplyRegistry).completeExceptionally(eq("req-1"), any(RuntimeException.class));
    }

    @Test
    @DisplayName("tokens 为 null 时默认 0")
    void consume_tokensNull_defaultsToZero() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        AiReplyEvent event = buildEvent();
        event.setTokens(null);
        Message savedMsg = new Message();
        savedMsg.setId(1L);
        savedMsg.setConversationId(1L);
        savedMsg.setContent("回答");
        savedMsg.setTokensUsed(0);
        when(messageRepository.save(any())).thenReturn(savedMsg);

        consumer.consume(event);

        ArgumentCaptor<Message> captor = ArgumentCaptor.forClass(Message.class);
        verify(messageRepository, times(2)).save(captor.capture());
        Message assistantMsg = captor.getAllValues().get(1);
        assertThat(assistantMsg.getTokensUsed()).isEqualTo(0);
    }
}
