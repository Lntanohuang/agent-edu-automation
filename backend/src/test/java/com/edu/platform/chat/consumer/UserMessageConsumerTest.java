package com.edu.platform.chat.consumer;

import com.edu.platform.chat.BaseUnitTest;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.event.UserChatMessageEvent;
import com.edu.platform.chat.service.AiModelClient;
import com.edu.platform.chat.service.ChatContextCacheService;
import com.edu.platform.chat.service.ChatEventPublisher;
import com.edu.platform.common.BusinessException;
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

@DisplayName("UserMessageConsumer 单元测试")
class UserMessageConsumerTest extends BaseUnitTest {

    @Mock
    private ChatContextCacheService cacheService;
    @Mock
    private AiModelClient aiModelClient;
    @Mock
    private ChatEventPublisher eventPublisher;

    @InjectMocks
    private UserMessageConsumer consumer;

    private UserChatMessageEvent buildEvent() {
        return UserChatMessageEvent.builder()
                .eventId("evt-1")
                .requestId("req-1")
                .traceId("trace-1")
                .conversationId(1L)
                .userId(100L)
                .message("什么是法律渊源？")
                .timestamp(System.currentTimeMillis())
                .build();
    }

    @Test
    @DisplayName("event 为 null 时直接返回")
    void consume_whenNull_doesNothing() {
        consumer.consume(null);
        verifyNoInteractions(cacheService, aiModelClient, eventPublisher);
    }

    @Test
    @DisplayName("eventId 为 null 时直接返回")
    void consume_whenEventIdNull_doesNothing() {
        consumer.consume(UserChatMessageEvent.builder().build());
        verifyNoInteractions(cacheService);
    }

    @Test
    @DisplayName("重复事件被跳过（幂等）")
    void consume_whenDuplicate_skips() {
        when(cacheService.markEventProcessed("user-consume:evt-1")).thenReturn(false);

        consumer.consume(buildEvent());

        verify(aiModelClient, never()).generateReply(anyString(), anyLong(), anyList());
        verify(eventPublisher, never()).publishAiReply(any());
    }

    @Test
    @DisplayName("正常流程：加载历史 → 调 AI → 发布回复")
    void consume_happyPath() {
        when(cacheService.markEventProcessed("user-consume:evt-1")).thenReturn(true);
        when(cacheService.loadHistory(1L, 20)).thenReturn(List.of());
        when(aiModelClient.generateReply(eq("什么是法律渊源？"), eq(1L), anyList()))
                .thenReturn(new AiModelClient.AiServiceReply(
                        "法律渊源是指...", "law_explain",
                        List.of("教材第三章"), List.of(), List.of("法理学"),
                        "high", List.of()));

        consumer.consume(buildEvent());

        ArgumentCaptor<AiReplyEvent> captor = ArgumentCaptor.forClass(AiReplyEvent.class);
        verify(eventPublisher).publishAiReply(captor.capture());
        AiReplyEvent reply = captor.getValue();
        assertThat(reply.getSuccess()).isTrue();
        assertThat(reply.getAnswer()).isEqualTo("法律渊源是指...");
        assertThat(reply.getSkillUsed()).isEqualTo("law_explain");
        assertThat(reply.getEventId()).isEqualTo("evt-1");
        assertThat(reply.getTokens()).isEqualTo("法律渊源是指...".length() / 2);
    }

    @Test
    @DisplayName("AI 抛出 BusinessException → 发布 fallback 回复")
    void consume_whenBusinessException_publishesFallback() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        when(cacheService.loadHistory(anyLong(), anyInt())).thenReturn(List.of());
        when(aiModelClient.generateReply(anyString(), anyLong(), anyList()))
                .thenThrow(new BusinessException(503, "AI 服务超时"));

        consumer.consume(buildEvent());

        ArgumentCaptor<AiReplyEvent> captor = ArgumentCaptor.forClass(AiReplyEvent.class);
        verify(eventPublisher).publishAiReply(captor.capture());
        assertThat(captor.getValue().getSuccess()).isFalse();
        assertThat(captor.getValue().getErrorMessage()).isEqualTo("AI 服务超时");
    }

    @Test
    @DisplayName("AI 抛出 RuntimeException → 发布通用 fallback")
    void consume_whenRuntimeException_publishesGenericFallback() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        when(cacheService.loadHistory(anyLong(), anyInt())).thenReturn(List.of());
        when(aiModelClient.generateReply(anyString(), anyLong(), anyList()))
                .thenThrow(new RuntimeException("连接超时"));

        consumer.consume(buildEvent());

        ArgumentCaptor<AiReplyEvent> captor = ArgumentCaptor.forClass(AiReplyEvent.class);
        verify(eventPublisher).publishAiReply(captor.capture());
        assertThat(captor.getValue().getSuccess()).isFalse();
        assertThat(captor.getValue().getAnswer()).contains("AI 服务暂时不可用");
    }

    @Test
    @DisplayName("发布 AI 回复失败 → 清除幂等 key 并重抛")
    void consume_whenPublishFails_clearsDigestAndRethrows() {
        when(cacheService.markEventProcessed(anyString())).thenReturn(true);
        when(cacheService.loadHistory(anyLong(), anyInt())).thenReturn(List.of());
        when(aiModelClient.generateReply(anyString(), anyLong(), anyList()))
                .thenReturn(new AiModelClient.AiServiceReply("回答", null, List.of(), List.of(), List.of(), null, List.of()));
        doThrow(new RuntimeException("MQ 发送失败")).when(eventPublisher).publishAiReply(any());

        assertThatThrownBy(() -> consumer.consume(buildEvent()))
                .isInstanceOf(RuntimeException.class);

        verify(cacheService).clearEventDigest("user-consume:evt-1");
    }
}
