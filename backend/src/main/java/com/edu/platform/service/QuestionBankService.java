package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.edu.platform.common.BusinessException;
import com.edu.platform.dto.QuestionGenerateRequest;
import com.edu.platform.dto.QuestionGenerateResponse;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import com.edu.platform.dto.QuestionReviewRequest;
import com.edu.platform.dto.QuestionReviewResponse;
import com.edu.platform.entity.QuestionBankItem;
import com.edu.platform.entity.QuestionGenerationDraft;
import com.edu.platform.repository.QuestionBankItemRepository;
import com.edu.platform.repository.QuestionGenerationDraftRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class QuestionBankService {

    private static final String QUESTION_GENERATE_ENDPOINT = "/question-gen/generate";
    private final QuestionGenerationDraftRepository draftRepository;
    private final QuestionBankItemRepository questionBankItemRepository;
    private final RestTemplate restTemplate = buildRestTemplate();

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    private static RestTemplate buildRestTemplate() {
        // AI 出题耗时最长 ~2-3 分钟，给 10 分钟读超时留余量
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout((int) Duration.ofSeconds(10).toMillis());
        factory.setReadTimeout((int) Duration.ofMinutes(10).toMillis());
        return new RestTemplate(factory);
    }

    /**
     * 生成题目：AI 调用在事务外，仅持久化步骤进入事务，避免
     * Hikari apparent connection leak（长耗时 AI 调用期间占用连接池）。
     */
    public QuestionGenerateResponse generate(Long userId, QuestionGenerateRequest request) {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        long startedAt = System.currentTimeMillis();
        log.info(
                "[question-gen] step=received traceId={} userId={} subject={} topic={} outputMode={} questionCount={}",
                traceId,
                userId,
                request.getSubject(),
                request.getTopic(),
                request.getOutputMode(),
                request.getQuestionCount()
        );

        JSONObject aiObject = callQuestionGeneration(request, traceId);
        JSONObject questionSet = aiObject.getJSONObject("question_set");
        if (questionSet == null) {
            throw new BusinessException(503, "出题服务返回为空");
        }
        JSONArray questions = questionSet.getJSONArray("questions");
        int actualCount = questions == null ? 0 : questions.size();
        if (actualCount == 0) {
            throw new BusinessException(503, "出题服务未返回题目");
        }
        log.info(
                "[question-gen] step=response_parsed traceId={} actualQuestionCount={} sourceCount={} bookLabelCount={} validationNoteCount={}",
                traceId,
                actualCount,
                toStringList(aiObject.getJSONArray("sources")).size(),
                toStringList(aiObject.getJSONArray("book_labels")).size(),
                toStringList(aiObject.getJSONArray("validation_notes")).size()
        );

        QuestionGenerationDraft draft = persistDraft(userId, request, questionSet, aiObject, actualCount);
        log.info(
                "[question-gen] step=draft_persisted traceId={} draftId={} reviewStatus={}",
                traceId,
                draft.getId(),
                draft.getReviewStatus()
        );
        log.info("[question-gen] step=completed traceId={} totalElapsedMs={}", traceId, System.currentTimeMillis() - startedAt);

        return QuestionGenerateResponse.builder()
                .draftId(draft.getId())
                .reviewStatus(draft.getReviewStatus().name())
                .message("生成成功，待教师审核")
                .generationMode(draft.getGenerationMode().name())
                .questionCount(actualCount)
                .questionSet(questionSet)
                .bookLabels(toStringList(aiObject.getJSONArray("book_labels")))
                .sources(toStringList(aiObject.getJSONArray("sources")))
                .validationNotes(toStringList(aiObject.getJSONArray("validation_notes")))
                .build();
    }

    /**
     * 持久化草稿。Spring Data JPA 的 save() 自带短事务，无需手动 @Transactional
     * 包裹，避免事务延展到上游的 AI 长耗时调用。
     */
    private QuestionGenerationDraft persistDraft(
            Long userId,
            QuestionGenerateRequest request,
            JSONObject questionSet,
            JSONObject aiObject,
            int actualCount
    ) {
        QuestionGenerationDraft draft = new QuestionGenerationDraft();
        draft.setUserId(userId);
        draft.setSubject(request.getSubject());
        draft.setTopic(request.getTopic());
        draft.setTextbookScope(JSON.toJSONString(request.getTextbookScope()));
        draft.setGenerationMode(parseMode(request.getOutputMode()));
        draft.setQuestionCount(actualCount);
        draft.setTotalScore(request.getTotalScore());
        draft.setReviewStatus(QuestionGenerationDraft.ReviewStatus.pending);
        draft.setTitle(resolveTitle(questionSet, request));
        draft.setAiPayload(aiObject.toJSONString());
        return draftRepository.save(draft);
    }

    public Page<Map<String, Object>> listDrafts(Long userId, Pageable pageable) {
        return draftRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable)
                .map(this::toDraftSummary);
    }

    public Map<String, Object> getDraftDetail(Long userId, Long draftId) {
        QuestionGenerationDraft draft = findOwnedDraft(userId, draftId);
        JSONObject aiPayload = parseAiPayload(draft.getAiPayload());
        JSONObject questionSet = aiPayload.getJSONObject("question_set");

        Map<String, Object> detail = new HashMap<>();
        detail.put("draftId", draft.getId());
        detail.put("title", draft.getTitle());
        detail.put("subject", draft.getSubject());
        detail.put("topic", draft.getTopic());
        detail.put("textbookScope", safeJsonArray(draft.getTextbookScope()));
        detail.put("generationMode", draft.getGenerationMode().name());
        detail.put("questionCount", draft.getQuestionCount());
        detail.put("totalScore", draft.getTotalScore());
        detail.put("reviewStatus", draft.getReviewStatus().name());
        detail.put("reviewNote", draft.getReviewNote());
        detail.put("questionSet", questionSet == null ? Map.of() : questionSet);
        detail.put("bookLabels", toStringList(aiPayload.getJSONArray("book_labels")));
        detail.put("sources", toStringList(aiPayload.getJSONArray("sources")));
        detail.put("validationNotes", toStringList(aiPayload.getJSONArray("validation_notes")));
        detail.put("importedCount", questionBankItemRepository.countByDraftId(draft.getId()));
        detail.put("createdAt", draft.getCreatedAt());
        detail.put("updatedAt", draft.getUpdatedAt());
        return detail;
    }

    @Transactional
    public QuestionReviewResponse reviewDraft(Long userId, Long draftId, QuestionReviewRequest request) {
        QuestionGenerationDraft draft = findOwnedDraft(userId, draftId);
        if (draft.getReviewStatus() != QuestionGenerationDraft.ReviewStatus.pending) {
            throw new BusinessException(400, "该草稿已审核，不能重复操作");
        }

        String action = request.getAction().trim().toLowerCase();
        if (!action.equals("approve") && !action.equals("reject")) {
            throw new BusinessException(400, "审核动作仅支持 approve/reject");
        }

        long importedCount = 0L;
        JSONObject aiPayload = parseAiPayload(draft.getAiPayload());
        JSONObject finalQuestionSet = aiPayload.getJSONObject("question_set");

        if (request.getEditedQuestionSet() != null && !request.getEditedQuestionSet().isEmpty()) {
            finalQuestionSet = JSONObject.from(request.getEditedQuestionSet());
            aiPayload.put("question_set", finalQuestionSet);
            draft.setAiPayload(aiPayload.toJSONString());
        }

        if (action.equals("approve")) {
            importedCount = importToQuestionBank(draft, finalQuestionSet);
            draft.setReviewStatus(QuestionGenerationDraft.ReviewStatus.approved);
            draft.setReviewNote(normalizeReviewNote(request.getReviewNote(), "审核通过并入库"));
        } else {
            draft.setReviewStatus(QuestionGenerationDraft.ReviewStatus.rejected);
            draft.setReviewNote(normalizeReviewNote(request.getReviewNote(), "审核驳回"));
        }

        draftRepository.save(draft);
        return QuestionReviewResponse.builder()
                .draftId(draft.getId())
                .reviewStatus(draft.getReviewStatus().name())
                .importedCount(importedCount)
                .message(action.equals("approve") ? "审核通过，已入库" : "已驳回草稿")
                .build();
    }

    public Page<Map<String, Object>> listQuestionBank(Long userId, Pageable pageable) {
        return questionBankItemRepository
                .findByUserIdAndStatusOrderByCreatedAtDesc(userId, QuestionBankItem.Status.active, pageable)
                .map(this::toQuestionBankItem);
    }

    @CircuitBreaker(name = "aiService", fallbackMethod = "callQuestionGenerationFallback")
    private JSONObject callQuestionGeneration(QuestionGenerateRequest request, String traceId) {
        try {
            long aiStartedAt = System.currentTimeMillis();
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.add("X-Trace-Id", traceId);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(buildAiRequestBody(request), headers);
            log.info(
                    "[question-gen] step=request_start traceId={} endpoint={}",
                    traceId,
                    aiServiceUrl + QUESTION_GENERATE_ENDPOINT
            );
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + QUESTION_GENERATE_ENDPOINT,
                    entity,
                    String.class
            );
            log.info(
                    "[question-gen] step=request_done traceId={} status={} elapsedMs={}",
                    traceId,
                    response.getStatusCode(),
                    System.currentTimeMillis() - aiStartedAt
            );
            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                throw new BusinessException(503, "出题服务响应异常");
            }
            JSONObject aiObject = JSON.parseObject(response.getBody());
            if (aiObject == null) {
                throw new BusinessException(503, "出题服务返回为空");
            }
            if (Boolean.FALSE.equals(aiObject.getBoolean("success"))) {
                String message = aiObject.getString("message");
                throw new BusinessException(503, message != null ? message : "出题服务失败");
            }
            return aiObject;
        } catch (Exception e) {
            log.error("[question-gen] step=request_error traceId={}", traceId, e);
            if (e instanceof BusinessException businessException) {
                throw businessException;
            }
            throw new BusinessException(503, "出题服务暂时不可用，请稍后再试");
        }
    }

    private JSONObject callQuestionGenerationFallback(QuestionGenerateRequest request, String traceId, Throwable ex) {
        log.warn("出题 AI 服务熔断降级, traceId={}, topic={}, error={}", traceId, request.getTopic(), ex.getMessage());
        throw new BusinessException(503, "AI 服务暂时不可用，请稍后重试");
    }

    private Map<String, Object> buildAiRequestBody(QuestionGenerateRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("subject", request.getSubject());
        body.put("topic", request.getTopic());
        body.put("textbook_scope", request.getTextbookScope() == null ? List.of() : request.getTextbookScope());
        body.put("question_count", request.getQuestionCount());
        body.put("question_types", request.getQuestionTypes() == null || request.getQuestionTypes().isEmpty()
                ? List.of("单选题", "多选题", "判断题", "填空题", "简答题", "案例分析题")
                : request.getQuestionTypes());
        body.put("output_mode", request.getOutputMode() == null ? "practice" : request.getOutputMode());
        body.put("total_score", request.getTotalScore());
        body.put("include_answer", request.getIncludeAnswer() == null || request.getIncludeAnswer());
        body.put("include_explanation", request.getIncludeExplanation() == null || request.getIncludeExplanation());
        body.put("require_source_citation", request.getRequireSourceCitation() == null || request.getRequireSourceCitation());

        Map<String, Object> difficulty = new HashMap<>();
        QuestionGenerateRequest.DifficultyDistribution distribution = request.getDifficultyDistribution() == null
                ? new QuestionGenerateRequest.DifficultyDistribution()
                : request.getDifficultyDistribution();
        difficulty.put("easy", distribution.getEasy());
        difficulty.put("medium", distribution.getMedium());
        difficulty.put("hard", distribution.getHard());
        body.put("difficulty_distribution", difficulty);
        return body;
    }

    private QuestionGenerationDraft findOwnedDraft(Long userId, Long draftId) {
        return draftRepository.findByIdAndUserId(draftId, userId)
                .orElseThrow(() -> new BusinessException(404, "题目草稿不存在"));
    }

    private QuestionGenerationDraft.GenerationMode parseMode(String outputMode) {
        if ("paper".equalsIgnoreCase(outputMode)) {
            return QuestionGenerationDraft.GenerationMode.paper;
        }
        return QuestionGenerationDraft.GenerationMode.practice;
    }

    private String resolveTitle(JSONObject questionSet, QuestionGenerateRequest request) {
        String title = questionSet.getString("title");
        if (title != null && !title.trim().isEmpty()) {
            return title.trim();
        }
        String modeName = "paper".equalsIgnoreCase(request.getOutputMode()) ? "试卷" : "练习题";
        return request.getSubject() + "-" + request.getTopic() + "-" + modeName;
    }

    private JSONObject parseAiPayload(String payload) {
        JSONObject object = JSON.parseObject(payload);
        if (object == null) {
            throw new BusinessException(500, "草稿数据损坏");
        }
        return object;
    }

    private long importToQuestionBank(QuestionGenerationDraft draft, JSONObject questionSet) {
        if (questionSet == null) {
            throw new BusinessException(400, "草稿缺少题目内容");
        }
        JSONArray questions = questionSet.getJSONArray("questions");
        if (questions == null || questions.isEmpty()) {
            throw new BusinessException(400, "草稿题目为空，无法入库");
        }

        List<QuestionBankItem> items = questions.stream()
                .filter(Objects::nonNull)
                .map(obj -> (JSONObject) obj)
                .map(question -> toQuestionBankEntity(draft, question))
                .toList();
        questionBankItemRepository.saveAll(items);
        return items.size();
    }

    private QuestionBankItem toQuestionBankEntity(QuestionGenerationDraft draft, JSONObject question) {
        QuestionBankItem item = new QuestionBankItem();
        item.setDraftId(draft.getId());
        item.setUserId(draft.getUserId());
        item.setSubject(draft.getSubject());
        item.setQuestionType(stringValue(question.get("question_type"), "简答题"));
        item.setDifficulty(stringValue(question.get("difficulty"), "中等"));
        item.setStem(stringValue(question.get("stem"), ""));
        item.setOptionsJson(toJsonArrayString(question.get("options")));
        item.setAnswerText(stringValue(question.get("answer"), ""));
        item.setExplanation(stringValue(question.get("explanation"), ""));
        item.setKnowledgePoints(toJsonArrayString(question.get("knowledge_points")));
        item.setSourceCitations(toJsonArrayString(question.get("source_citations")));
        item.setScore(toBigDecimal(question.get("score")));
        item.setStatus(QuestionBankItem.Status.active);
        if (item.getStem().isBlank() || item.getAnswerText().isBlank() || item.getExplanation().isBlank()) {
            throw new BusinessException(400, "题目存在空题干、答案或解析，无法入库");
        }
        return item;
    }

    private Map<String, Object> toDraftSummary(QuestionGenerationDraft draft) {
        Map<String, Object> summary = new HashMap<>();
        summary.put("draftId", draft.getId());
        summary.put("title", draft.getTitle());
        summary.put("subject", draft.getSubject());
        summary.put("topic", draft.getTopic());
        summary.put("generationMode", draft.getGenerationMode().name());
        summary.put("questionCount", draft.getQuestionCount());
        summary.put("totalScore", draft.getTotalScore());
        summary.put("reviewStatus", draft.getReviewStatus().name());
        summary.put("importedCount", questionBankItemRepository.countByDraftId(draft.getId()));
        summary.put("createdAt", draft.getCreatedAt());
        summary.put("updatedAt", draft.getUpdatedAt());
        return summary;
    }

    private Map<String, Object> toQuestionBankItem(QuestionBankItem item) {
        Map<String, Object> data = new HashMap<>();
        data.put("id", item.getId());
        data.put("draftId", item.getDraftId());
        data.put("subject", item.getSubject());
        data.put("questionType", item.getQuestionType());
        data.put("difficulty", item.getDifficulty());
        data.put("stem", item.getStem());
        data.put("options", safeJsonArray(item.getOptionsJson()));
        data.put("answer", item.getAnswerText());
        data.put("explanation", item.getExplanation());
        data.put("knowledgePoints", safeJsonArray(item.getKnowledgePoints()));
        data.put("sourceCitations", safeJsonArray(item.getSourceCitations()));
        data.put("score", item.getScore());
        data.put("status", item.getStatus().name());
        data.put("createdAt", item.getCreatedAt());
        return data;
    }

    private List<String> toStringList(JSONArray array) {
        if (array == null || array.isEmpty()) {
            return List.of();
        }
        return array.stream().map(String::valueOf).toList();
    }

    private JSONArray safeJsonArray(String value) {
        if (value == null || value.isBlank()) {
            return new JSONArray();
        }
        JSONArray arr = JSON.parseArray(value);
        return arr == null ? new JSONArray() : arr;
    }

    private String toJsonArrayString(Object value) {
        if (value == null) {
            return "[]";
        }
        if (value instanceof JSONArray arr) {
            return arr.toJSONString();
        }
        if (value instanceof List<?> list) {
            return JSON.toJSONString(list);
        }
        return JSON.toJSONString(List.of(String.valueOf(value)));
    }

    private String stringValue(Object value, String defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? defaultValue : text;
    }

    private BigDecimal toBigDecimal(Object value) {
        if (value == null) {
            return BigDecimal.ZERO;
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception ignored) {
            return BigDecimal.ZERO;
        }
    }

    private String normalizeReviewNote(String reviewNote, String fallback) {
        if (reviewNote == null || reviewNote.trim().isEmpty()) {
            return fallback;
        }
        return reviewNote.trim();
    }
}
