package com.edu.platform.chat.event;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AiReplyEvent {

    private String eventId;
    private String requestId;
    private String traceId;
    private Long conversationId;
    private Long userId;
    private String userMessage;
    private String answer;
    private Integer tokens;
    private String skillUsed;
    private List<String> sources;
    private List<String> explorationTasks;
    private List<String> bookLabels;
    private String confidence;
    private List<String> auditNotes;
    private Boolean success;
    private String errorMessage;
    private Long timestamp;
}
