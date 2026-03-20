package com.edu.platform.chat.service;

import com.edu.platform.dto.ChatMessageResponse;
import org.springframework.stereotype.Component;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

@Component
public class ChatPendingReplyRegistry {

    private final ConcurrentMap<String, CompletableFuture<ChatMessageResponse>> pendingReplies = new ConcurrentHashMap<>();

    public CompletableFuture<ChatMessageResponse> register(String requestId) {
        CompletableFuture<ChatMessageResponse> future = new CompletableFuture<>();
        pendingReplies.put(requestId, future);
        return future;
    }

    public void complete(String requestId, ChatMessageResponse response) {
        CompletableFuture<ChatMessageResponse> future = pendingReplies.remove(requestId);
        if (future != null) {
            future.complete(response);
        }
    }

    public void completeExceptionally(String requestId, Throwable throwable) {
        CompletableFuture<ChatMessageResponse> future = pendingReplies.remove(requestId);
        if (future != null) {
            future.completeExceptionally(throwable);
        }
    }

    public void cleanup(String requestId) {
        pendingReplies.remove(requestId);
    }
}
