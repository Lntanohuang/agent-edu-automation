package com.edu.platform.chat.consumer;

import com.edu.platform.chat.BaseUnitTest;
import com.edu.platform.chat.event.AiReplyEvent;
import com.edu.platform.chat.service.ChatWebSocketNotifier;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;

import static org.mockito.Mockito.*;

@DisplayName("AiReplyDeliveryConsumer 单元测试")
class AiReplyDeliveryConsumerTest extends BaseUnitTest {

    @Mock
    private ChatWebSocketNotifier webSocketNotifier;

    @InjectMocks
    private AiReplyDeliveryConsumer consumer;

    @Test
    @DisplayName("event 为 null 时不推送")
    void consume_whenNull_doesNothing() {
        consumer.consume(null);
        verifyNoInteractions(webSocketNotifier);
    }

    @Test
    @DisplayName("eventId 为 null 时不推送")
    void consume_whenEventIdNull_doesNothing() {
        consumer.consume(AiReplyEvent.builder().build());
        verifyNoInteractions(webSocketNotifier);
    }

    @Test
    @DisplayName("正常事件 → pushToUser")
    void consume_happyPath_callsPushToUser() {
        AiReplyEvent event = AiReplyEvent.builder()
                .eventId("evt-1").requestId("req-1").answer("回答").build();

        consumer.consume(event);

        verify(webSocketNotifier).pushToUser(event);
    }
}
