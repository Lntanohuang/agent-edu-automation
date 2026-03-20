package com.edu.platform.chat.mongo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.CompoundIndexes;
import org.springframework.data.mongodb.core.mapping.Document;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "chat_messages")
@CompoundIndexes({
        @CompoundIndex(name = "uk_event_role", def = "{'eventId': 1, 'role': 1}", unique = true),
        @CompoundIndex(name = "idx_conversation_ts", def = "{'conversationId': 1, 'timestamp': 1}")
})
public class ChatMessageArchive {

    @Id
    private String id;
    private String eventId;
    private String requestId;
    private String traceId;
    private Long conversationId;
    private Long userId;
    private String role;
    private String content;
    private Integer tokensUsed;
    private String metadata;
    private Long timestamp;
}
