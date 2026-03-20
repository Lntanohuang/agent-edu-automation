package com.edu.platform.chat.service;

import com.edu.platform.dto.ChatMessageResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DisplayName("ChatPendingReplyRegistry 纯逻辑测试")
class ChatPendingReplyRegistryTest {

    private ChatPendingReplyRegistry registry;

    @BeforeEach
    void setUp() {
        registry = new ChatPendingReplyRegistry();
    }

    @Test
    @DisplayName("register 返回新的 CompletableFuture")
    void register_returnsNewFuture() {
        CompletableFuture<ChatMessageResponse> future = registry.register("req-1");

        assertThat(future).isNotNull();
        assertThat(future.isDone()).isFalse();
    }

    @Test
    @DisplayName("complete 后 future 得到结果")
    void complete_resolvesFuture() throws Exception {
        CompletableFuture<ChatMessageResponse> future = registry.register("req-1");
        ChatMessageResponse response = ChatMessageResponse.builder()
                .content("回答").build();

        registry.complete("req-1", response);

        assertThat(future.get(1, TimeUnit.SECONDS).getContent()).isEqualTo("回答");
    }

    @Test
    @DisplayName("complete 未注册的 requestId 不抛异常")
    void complete_whenNotRegistered_doesNotThrow() {
        registry.complete("unknown", ChatMessageResponse.builder().build());
        // 不抛异常就是成功
    }

    @Test
    @DisplayName("completeExceptionally 后 future 抛异常")
    void completeExceptionally_failsFuture() {
        CompletableFuture<ChatMessageResponse> future = registry.register("req-1");

        registry.completeExceptionally("req-1", new RuntimeException("DB 错误"));

        assertThatThrownBy(() -> future.get(1, TimeUnit.SECONDS))
                .isInstanceOf(ExecutionException.class)
                .hasCauseInstanceOf(RuntimeException.class)
                .hasMessageContaining("DB 错误");
    }

    @Test
    @DisplayName("cleanup 移除后再 complete 无效")
    void cleanup_removesEntry() throws Exception {
        CompletableFuture<ChatMessageResponse> future = registry.register("req-1");

        registry.cleanup("req-1");
        registry.complete("req-1", ChatMessageResponse.builder().content("不应该收到").build());

        // future 未被 complete，仍然 pending
        assertThat(future.isDone()).isFalse();
    }

    @Test
    @DisplayName("二次 register 同一 ID 覆盖前一个")
    void register_twiceSameId_overwritesPrevious() throws Exception {
        CompletableFuture<ChatMessageResponse> first = registry.register("req-1");
        CompletableFuture<ChatMessageResponse> second = registry.register("req-1");

        registry.complete("req-1", ChatMessageResponse.builder().content("给第二个").build());

        assertThat(second.get(1, TimeUnit.SECONDS).getContent()).isEqualTo("给第二个");
        // 第一个被覆盖，不会被 complete
        assertThat(first.isDone()).isFalse();
    }
}
