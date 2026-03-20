package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.edu.platform.common.BusinessException;
import com.edu.platform.dto.PlanAgentGenerateRequest;
import com.edu.platform.dto.PlanAgentGenerateResponse;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
public class PlanAgentService {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    @CircuitBreaker(name = "aiService", fallbackMethod = "generatePlanFallback")
    public PlanAgentGenerateResponse generatePlan(PlanAgentGenerateRequest request) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

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

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + "/plan-agent/generate",
                    entity,
                    String.class
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

            return PlanAgentGenerateResponse.builder()
                    .success(true)
                    .message(message != null ? message : "生成成功")
                    .semesterPlan(semesterPlan)
                    .build();
        } catch (Exception e) {
            log.error("调用教案服务失败", e);
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
}
