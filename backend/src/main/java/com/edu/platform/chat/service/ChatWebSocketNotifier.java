package com.edu.platform.chat.service;

import com.edu.platform.chat.event.AiReplyEvent;
import lombok.RequiredArgsConstructor;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ChatWebSocketNotifier {

    private final SimpMessagingTemplate messagingTemplate;

    public void pushToUser(AiReplyEvent event) {
        messagingTemplate.convertAndSend("/topic/chat/user/" + event.getUserId(), buildPayload(event));
    }

    public void pushToAdmin(AiReplyEvent event) {
        messagingTemplate.convertAndSend("/topic/chat/admin", buildPayload(event));
    }

    private Map<String, Object> buildPayload(AiReplyEvent event) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("requestId", event.getRequestId());
        payload.put("conversationId", event.getConversationId());
        payload.put("userId", event.getUserId());
        payload.put("success", event.getSuccess());
        payload.put("content", event.getAnswer());
        payload.put("timestamp", event.getTimestamp());
        payload.put("skillUsed", event.getSkillUsed());
        payload.put("sources", event.getSources());
        payload.put("explorationTasks", event.getExplorationTasks());
        payload.put("bookLabels", event.getBookLabels());
        payload.put("confidence", event.getConfidence());
        payload.put("auditNotes", event.getAuditNotes());
        payload.put("errorMessage", event.getErrorMessage());
        return payload;
    }
}
