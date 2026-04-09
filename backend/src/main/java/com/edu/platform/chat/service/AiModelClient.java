package com.edu.platform.chat.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.edu.platform.common.BusinessException;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class AiModelClient {

    private static final int MAX_HISTORY_TOKENS = 512;
    private static final String AI_CHAT_ENDPOINT = "/rag/agent/chat";
    private final RestTemplate restTemplate;

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    public AiModelClient(@Value("${ai.service.timeout:180000}") int aiServiceTimeoutMs) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Math.min(aiServiceTimeoutMs, 30000));
        requestFactory.setReadTimeout(aiServiceTimeoutMs);
        this.restTemplate = new RestTemplate(requestFactory);
    }

    @CircuitBreaker(name = "aiService", fallbackMethod = "generateReplyFallback")
    public AiServiceReply generateReply(String query,
                                        Long conversationId,
                                        List<ChatContextCacheService.HistoryMessage> historyMessages) {
        return doGenerateReply(query, conversationId, historyMessages, null);
    }

    @CircuitBreaker(name = "aiService", fallbackMethod = "generateReplyWithTraceFallback")
    public AiServiceReply generateReplyWithTrace(String query,
                                                 Long conversationId,
                                                 List<ChatContextCacheService.HistoryMessage> historyMessages,
                                                 String traceId) {
        return doGenerateReply(query, conversationId, historyMessages, traceId);
    }

    private AiServiceReply doGenerateReply(String query,
                                           Long conversationId,
                                           List<ChatContextCacheService.HistoryMessage> historyMessages,
                                           String traceId) {
        String safeTraceId = traceId == null || traceId.isBlank() ? "-" : traceId;
        long startedAt = System.currentTimeMillis();
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            if (!"-".equals(safeTraceId)) {
                headers.add("X-Trace-Id", safeTraceId);
            }
            HttpEntity<Map<String, Object>> entity =
                    new HttpEntity<>(buildAiRequestBody(query, conversationId, historyMessages), headers);

            log.info(
                    "[ai-client] step=request_start traceId={} conversationId={} endpoint={} queryChars={} historyCount={}",
                    safeTraceId,
                    conversationId,
                    aiServiceUrl + AI_CHAT_ENDPOINT,
                    query == null ? 0 : query.length(),
                    historyMessages == null ? 0 : historyMessages.size()
            );
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + AI_CHAT_ENDPOINT,
                    entity,
                    String.class
            );
            log.info(
                    "[ai-client] step=request_done traceId={} conversationId={} elapsedMs={} status={}",
                    safeTraceId,
                    conversationId,
                    System.currentTimeMillis() - startedAt,
                    response.getStatusCode()
            );

            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                throw new BusinessException(503, "AI 服务响应异常");
            }

            JSONObject obj = JSON.parseObject(response.getBody());
            if (obj == null) {
                throw new BusinessException(503, "AI 服务返回为空");
            }

            Boolean success = obj.getBoolean("success");
            if (Boolean.FALSE.equals(success)) {
                String error = obj.getString("error");
                String messageText = obj.getString("message");
                throw new BusinessException(503, "AI 服务失败: " + (error != null ? error : messageText));
            }

            String answer = obj.getString("answer") == null ? "" : obj.getString("answer").trim();
            if (answer.isEmpty()) {
                throw new BusinessException(503, "AI 服务返回空内容");
            }

            List<String> sources = toStringList(obj.getJSONArray("sources"));
            List<String> explorationTasks = toStringList(obj.getJSONArray("exploration_tasks"));
            List<String> bookLabels = toStringList(obj.getJSONArray("book_labels"));
            String skillUsed = obj.getString("skill_used");
            String confidence = obj.getString("confidence");

            log.info(
                    "[ai-client] step=response_parsed traceId={} conversationId={} skillUsed={} confidence={} sourceCount={} taskCount={} bookLabelCount={}",
                    safeTraceId,
                    conversationId,
                    skillUsed,
                    confidence,
                    sources.size(),
                    explorationTasks.size(),
                    bookLabels.size()
            );

            return new AiServiceReply(
                    answer,
                    skillUsed,
                    sources,
                    explorationTasks,
                    bookLabels,
                    confidence,
                    toStringList(obj.getJSONArray("audit_notes"))
            );
        } catch (BusinessException e) {
            log.warn(
                    "[ai-client] step=business_error traceId={} conversationId={} elapsedMs={} message={}",
                    safeTraceId,
                    conversationId,
                    System.currentTimeMillis() - startedAt,
                    e.getMessage()
            );
            throw e;
        } catch (Exception e) {
            log.error(
                    "[ai-client] step=request_error traceId={} conversationId={} elapsedMs={}",
                    safeTraceId,
                    conversationId,
                    System.currentTimeMillis() - startedAt,
                    e
            );
            throw new BusinessException(503, "AI 服务暂时不可用，请稍后再试");
        }
    }

    private AiServiceReply generateReplyFallback(String query,
                                                  Long conversationId,
                                                  List<ChatContextCacheService.HistoryMessage> historyMessages,
                                                  Throwable ex) {
        log.warn("AI 服务熔断降级, traceId=-, conversationId={}, error={}", conversationId, ex.getMessage());
        return new AiServiceReply(
                "AI 服务暂时不可用，请稍后重试",
                null,
                List.of(),
                List.of(),
                List.of(),
                null,
                List.of()
        );
    }

    private AiServiceReply generateReplyWithTraceFallback(String query,
                                                          Long conversationId,
                                                          List<ChatContextCacheService.HistoryMessage> historyMessages,
                                                          String traceId,
                                                          Throwable ex) {
        String safeTraceId = traceId == null || traceId.isBlank() ? "-" : traceId;
        log.warn("AI 服务熔断降级, traceId={}, conversationId={}, error={}", safeTraceId, conversationId, ex.getMessage());
        return new AiServiceReply(
                "AI 服务暂时不可用，请稍后重试",
                null,
                List.of(),
                List.of(),
                List.of(),
                null,
                List.of()
        );
    }

    private Map<String, Object> buildAiRequestBody(String message,
                                                   Long conversationId,
                                                   List<ChatContextCacheService.HistoryMessage> historyMessages) {
        List<Map<String, String>> history = historyMessages.stream()
                .map(item -> Map.of(
                        "role", "assistant".equalsIgnoreCase(item.getRole()) ? "assistant" : "user",
                        "content", item.getContent()
                ))
                .toList();

        Map<String, Object> body = new HashMap<>();
        body.put("query", message);
        body.put("conversation_id", String.valueOf(conversationId));
        body.put("history", history);
        body.put("max_history_tokens", MAX_HISTORY_TOKENS);
        return body;
    }

    private List<String> toStringList(JSONArray array) {
        if (array == null || array.isEmpty()) {
            return List.of();
        }
        return array.stream().map(String::valueOf).toList();
    }

    public record AiServiceReply(
            String answer,
            String skillUsed,
            List<String> sources,
            List<String> explorationTasks,
            List<String> bookLabels,
            String confidence,
            List<String> auditNotes
    ) {
    }
}
