package com.edu.platform.dto;

import com.edu.platform.entity.Conversation;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 对话列表项 DTO
 * 
 * 响应示例:
 * {
 *   "id": 1,
 *   "title": "如何设计数学课",
 *   "lastMessage": "谢谢你的建议",
 *   "messageCount": 12,
 *   "createdAt": "2024-01-15T10:00:00",
 *   "updatedAt": "2024-01-15T10:30:00"
 * }
 */
@Data
@Builder
public class ConversationDTO {

    private Long id;
    private String title;
    private String lastMessage;
    private Integer messageCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static ConversationDTO fromEntity(Conversation conversation, String lastMessage) {
        return ConversationDTO.builder()
                .id(conversation.getId())
                .title(conversation.getTitle())
                .lastMessage(lastMessage)
                .messageCount(conversation.getMessageCount())
                .createdAt(conversation.getCreatedAt())
                .updatedAt(conversation.getUpdatedAt())
                .build();
    }
}
