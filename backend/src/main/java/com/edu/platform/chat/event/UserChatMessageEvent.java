package com.edu.platform.chat.event;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserChatMessageEvent {

    private String eventId;
    private String requestId;
    private String traceId;
    private Long conversationId;
    private Long userId;
    private String message;
    private Map<String, String> context;
    private Long timestamp;
}
