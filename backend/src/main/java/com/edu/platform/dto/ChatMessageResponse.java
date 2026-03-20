package com.edu.platform.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 消息响应 DTO
 * 
 * 响应示例:
 * {
 *   "messageId": 100,
 *   "conversationId": 1,
 *   "content": "这是一个很好的教学问题！我建议您可以从以下几个方面考虑...",
 *   "role": "assistant",
 *   "timestamp": "2024-01-15T10:30:00",
 *   "tokens": 150
 * }
 */
@Data
@Builder
public class ChatMessageResponse {

    private Long messageId;
    private Long conversationId;
    private String content;
    private String role;
    private LocalDateTime timestamp;
    private Integer tokens;
    private String skillUsed;
    private List<String> sources;
    private List<String> explorationTasks;
    private List<String> bookLabels;
    private String confidence;
    private List<String> auditNotes;
}
