package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.edu.platform.common.BusinessException;
import com.edu.platform.dto.LessonPlanUpdateRequest;
import com.edu.platform.dto.PlanAgentGenerateRequest;
import com.edu.platform.dto.PlanAgentGenerateResponse;
import com.edu.platform.dto.PlanAgentV2GenerateResponse;
import com.edu.platform.entity.LessonPlan;
import com.edu.platform.repository.LessonPlanRepository;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
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
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
public class PlanAgentService {

    private static final String PLAN_V1_ENDPOINT = "/plan-agent/generate";
    private static final String PLAN_V2_ENDPOINT = "/plan-agent-v2/generate";
    private final RestTemplate restTemplate = buildRestTemplate();
    private final LessonPlanRepository lessonPlanRepository;

    private static RestTemplate buildRestTemplate() {
        // AI 服务教案生成耗时最长约 6-7 分钟，给 10 分钟读超时留余量
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout((int) Duration.ofSeconds(10).toMillis());
        factory.setReadTimeout((int) Duration.ofMinutes(10).toMillis());
        return new RestTemplate(factory);
    }

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    public PlanAgentService(LessonPlanRepository lessonPlanRepository) {
        this.lessonPlanRepository = lessonPlanRepository;
    }

    // ==================== V1 接口（保持不变） ====================

    @CircuitBreaker(name = "aiService", fallbackMethod = "generatePlanFallback")
    public PlanAgentGenerateResponse generatePlan(PlanAgentGenerateRequest request) {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        long startedAt = System.currentTimeMillis();
        log.info(
                "[plan-v1] step=received traceId={} subject={} topic={} totalWeeks={} lessonsPerWeek={}",
                traceId,
                request.getSubject(),
                request.getTopic(),
                request.getTotalWeeks(),
                request.getLessonsPerWeek()
        );
        try {
            long aiStartedAt = System.currentTimeMillis();
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.add("X-Trace-Id", traceId);

            Map<String, Object> body = buildRequestBody(request);
            log.info(
                    "[plan-v1] step=request_start traceId={} endpoint={} bodyKeys={}",
                    traceId,
                    aiServiceUrl + PLAN_V1_ENDPOINT,
                    body.keySet()
            );

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + PLAN_V1_ENDPOINT,
                    entity,
                    String.class
            );
            log.info(
                    "[plan-v1] step=request_done traceId={} status={} elapsedMs={}",
                    traceId,
                    response.getStatusCode(),
                    System.currentTimeMillis() - aiStartedAt
            );

            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                throw new BusinessException(503, "教案服务响应异常");
            }

            JSONObject obj = JSON.parseObject(response.getBody());
            if (obj == null) {
                throw new BusinessException(503, "教案服务返回为空");
            }

            boolean success = Boolean.TRUE.equals(obj.getBoolean("success"));
            String message = obj.getString("message");
            JSONObject semesterPlanObj = obj.getJSONObject("semester_plan");

            if (!success) {
                throw new BusinessException(503, message != null ? message : "教案生成失败");
            }

            Map<String, Object> semesterPlan = semesterPlanObj == null
                    ? Map.of()
                    : semesterPlanObj;
            log.info(
                    "[plan-v1] step=response_parsed traceId={} success={} hasSemesterPlan={}",
                    traceId,
                    success,
                    !semesterPlan.isEmpty()
            );
            log.info("[plan-v1] step=completed traceId={} totalElapsedMs={}", traceId, System.currentTimeMillis() - startedAt);

            return PlanAgentGenerateResponse.builder()
                    .success(true)
                    .message(message != null ? message : "生成成功")
                    .semesterPlan(semesterPlan)
                    .build();
        } catch (Exception e) {
            log.error("[plan-v1] step=error traceId={}", traceId, e);
            if (e instanceof BusinessException businessException) {
                throw businessException;
            }
            throw new BusinessException(503, "教案服务暂时不可用，请稍后再试");
        }
    }

    private PlanAgentGenerateResponse generatePlanFallback(PlanAgentGenerateRequest request, Throwable ex) {
        log.warn("教案 AI 服务熔断降级, topic={}, error={}", request.getTopic(), ex.getMessage());
        return PlanAgentGenerateResponse.builder()
                .success(false)
                .message("AI 服务暂时不可用，请稍后重试")
                .semesterPlan(Map.of())
                .build();
    }

    // ==================== V2 接口 ====================

    /**
     * V2: 调用 Multi-Agent Supervisor 生成学期计划，并持久化到数据库
     */
    @CircuitBreaker(name = "aiService", fallbackMethod = "generatePlanV2Fallback")
    public PlanAgentV2GenerateResponse generatePlanV2(PlanAgentGenerateRequest request, Long userId) {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        long startedAt = System.currentTimeMillis();
        log.info(
                "[plan-v2] step=received traceId={} userId={} subject={} topic={} totalWeeks={} lessonsPerWeek={}",
                traceId,
                userId,
                request.getSubject(),
                request.getTopic(),
                request.getTotalWeeks(),
                request.getLessonsPerWeek()
        );
        try {
            long aiStartedAt = System.currentTimeMillis();
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.add("X-Trace-Id", traceId);

            Map<String, Object> body = buildRequestBody(request);
            log.info(
                    "[plan-v2] step=request_start traceId={} endpoint={} bodyKeys={}",
                    traceId,
                    aiServiceUrl + PLAN_V2_ENDPOINT,
                    body.keySet()
            );

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + PLAN_V2_ENDPOINT,
                    entity,
                    String.class
            );
            log.info(
                    "[plan-v2] step=request_done traceId={} status={} elapsedMs={}",
                    traceId,
                    response.getStatusCode(),
                    System.currentTimeMillis() - aiStartedAt
            );

            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                throw new BusinessException(503, "教案服务响应异常");
            }

            JSONObject obj = JSON.parseObject(response.getBody());
            if (obj == null) {
                throw new BusinessException(503, "教案服务返回为空");
            }

            boolean success = Boolean.TRUE.equals(obj.getBoolean("success"));
            String message = obj.getString("message");
            JSONObject semesterPlanObj = obj.getJSONObject("semester_plan");
            JSONObject agentMetaObj = obj.getJSONObject("agent_meta");

            if (!success) {
                throw new BusinessException(503, message != null ? message : "教案生成失败");
            }

            Map<String, Object> semesterPlan = semesterPlanObj == null ? Map.of() : semesterPlanObj;
            Map<String, Object> agentMeta = agentMetaObj == null ? Map.of() : agentMetaObj;
            log.info(
                    "[plan-v2] step=response_parsed traceId={} success={} hasSemesterPlan={} hasAgentMeta={}",
                    traceId,
                    success,
                    !semesterPlan.isEmpty(),
                    !agentMeta.isEmpty()
            );

            // 持久化到 lesson_plans 表
            LessonPlan plan = new LessonPlan();
            plan.setUserId(userId);
            plan.setTitle(buildTitle(request));
            plan.setSubject(request.getSubject());
            plan.setGrade(request.getGrade());
            plan.setTopic(request.getTopic());
            plan.setClassSize(request.getClassSize());
            plan.setTextbookVersion(request.getTextbookVersion());
            plan.setDifficulty(request.getDifficulty());
            plan.setSemesterPlanJson(JSON.toJSONString(semesterPlan));
            plan.setAgentMetaJson(JSON.toJSONString(agentMeta));
            plan.setStatus(LessonPlan.Status.generated);

            LessonPlan saved = lessonPlanRepository.save(plan);
            log.info(
                    "[plan-v2] step=persisted traceId={} planId={} userId={}",
                    traceId,
                    saved.getId(),
                    userId
            );
            log.info("[plan-v2] step=completed traceId={} totalElapsedMs={}", traceId, System.currentTimeMillis() - startedAt);

            return PlanAgentV2GenerateResponse.builder()
                    .success(true)
                    .message(message != null ? message : "生成成功")
                    .planId(saved.getId())
                    .semesterPlan(semesterPlan)
                    .agentMeta(agentMeta)
                    .build();
        } catch (Exception e) {
            log.error("[plan-v2] step=error traceId={} userId={}", traceId, userId, e);
            if (e instanceof BusinessException businessException) {
                throw businessException;
            }
            throw new BusinessException(503, "教案服务暂时不可用，请稍后再试");
        }
    }

    private PlanAgentV2GenerateResponse generatePlanV2Fallback(PlanAgentGenerateRequest request, Long userId, Throwable ex) {
        log.warn("教案 V2 AI 服务熔断降级, topic={}, error={}", request.getTopic(), ex.getMessage());
        return PlanAgentV2GenerateResponse.builder()
                .success(false)
                .message("AI 服务暂时不可用，请稍后重试")
                .semesterPlan(Map.of())
                .agentMeta(Map.of())
                .build();
    }

    /**
     * 查询用户的教案历史（分页）
     */
    public Page<LessonPlan> getHistory(Long userId, Pageable pageable) {
        return lessonPlanRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    /**
     * 获取单个教案详情
     */
    public LessonPlan getPlanById(Long id) {
        return lessonPlanRepository.findById(id)
                .orElseThrow(() -> new BusinessException(404, "教案不存在"));
    }

    /**
     * 教师编辑教案
     */
    public LessonPlan updatePlan(Long id, Long userId, LessonPlanUpdateRequest request) {
        LessonPlan plan = lessonPlanRepository.findById(id)
                .orElseThrow(() -> new BusinessException(404, "教案不存在"));

        if (!plan.getUserId().equals(userId)) {
            throw new BusinessException(403, "无权修改他人教案");
        }

        if (request.getTitle() != null) plan.setTitle(request.getTitle());
        if (request.getSubject() != null) plan.setSubject(request.getSubject());
        if (request.getGrade() != null) plan.setGrade(request.getGrade());
        if (request.getTopic() != null) plan.setTopic(request.getTopic());
        if (request.getDuration() != null) plan.setDuration(request.getDuration());
        if (request.getClassSize() != null) plan.setClassSize(request.getClassSize());
        if (request.getTextbookVersion() != null) plan.setTextbookVersion(request.getTextbookVersion());
        if (request.getDifficulty() != null) plan.setDifficulty(request.getDifficulty());
        if (request.getHomework() != null) plan.setHomework(request.getHomework());
        if (request.getBlackboardDesign() != null) plan.setBlackboardDesign(request.getBlackboardDesign());
        if (request.getReflection() != null) plan.setReflection(request.getReflection());
        if (request.getSemesterPlanJson() != null) plan.setSemesterPlanJson(request.getSemesterPlanJson());
        if (request.getStatus() != null) {
            plan.setStatus(LessonPlan.Status.valueOf(request.getStatus()));
        }

        return lessonPlanRepository.save(plan);
    }

    /**
     * 删除教案
     */
    public void deletePlan(Long id, Long userId) {
        LessonPlan plan = lessonPlanRepository.findById(id)
                .orElseThrow(() -> new BusinessException(404, "教案不存在"));

        if (!plan.getUserId().equals(userId)) {
            throw new BusinessException(403, "无权删除他人教案");
        }

        lessonPlanRepository.deleteById(id);
    }

    // ==================== 私有工具方法 ====================

    /**
     * 构建发送到 AI 服务的请求体
     */
    private Map<String, Object> buildRequestBody(PlanAgentGenerateRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("subject", request.getSubject());
        body.put("grade", request.getGrade());
        body.put("topic", request.getTopic());
        body.put("total_weeks", request.getTotalWeeks());
        body.put("lessons_per_week", request.getLessonsPerWeek());
        body.put("class_size", request.getClassSize());
        body.put("course_type", request.getCourseType());
        body.put("credits", request.getCredits());
        body.put("assessment_mode", request.getAssessmentMode());
        body.put("teaching_goals", request.getTeachingGoals());
        body.put("requirements", request.getRequirements());
        body.put("textbook_version", request.getTextbookVersion());
        body.put("difficulty", request.getDifficulty());
        body.put("trace_project_name", request.getTraceProjectName());
        return body;
    }

    /**
     * 根据请求参数生成教案标题
     */
    private String buildTitle(PlanAgentGenerateRequest request) {
        String subject = request.getSubject() != null ? request.getSubject() : "课程";
        String topic = request.getTopic() != null ? request.getTopic() : "";
        if (!topic.isEmpty()) {
            return subject + " - " + topic;
        }
        return subject + " 学期计划";
    }
}
