package com.edu.platform.controller;

import com.edu.platform.common.Result;
import com.edu.platform.dto.LessonPlanUpdateRequest;
import com.edu.platform.dto.PlanAgentGenerateRequest;
import com.edu.platform.dto.PlanAgentGenerateResponse;
import com.edu.platform.dto.PlanAgentV2GenerateResponse;
import com.edu.platform.entity.LessonPlan;
import com.edu.platform.service.PlanAgentService;
import com.edu.platform.util.JwtUtil;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/plan-agent")
@RequiredArgsConstructor
public class PlanAgentController {

    private final PlanAgentService planAgentService;
    private final JwtUtil jwtUtil;

    // ==================== V1 接口（保持不变） ====================

    @PostMapping("/generate")
    public Result<PlanAgentGenerateResponse> generate(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody PlanAgentGenerateRequest request) {
        // 保持与现有接口一致：校验并解析登录态
        String token = authHeader.replace("Bearer ", "");
        jwtUtil.getUserIdFromToken(token);
        return Result.success(planAgentService.generatePlan(request));
    }

    // ==================== V2 接口 ====================

    /**
     * V2: Multi-Agent Supervisor 生成学期计划，持久化并返回 agent_meta
     */
    @PostMapping("/v2/generate")
    public Result<PlanAgentV2GenerateResponse> generateV2(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody PlanAgentGenerateRequest request) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        return Result.success(planAgentService.generatePlanV2(request, userId));
    }

    /**
     * V2: 查询当前用户的教案历史（分页）
     */
    @GetMapping("/v2/history")
    public Result<Page<LessonPlan>> history(
            @RequestHeader("Authorization") String authHeader,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        Pageable pageable = PageRequest.of(page, size);
        return Result.success(planAgentService.getHistory(userId, pageable));
    }

    /**
     * V2: 获取单个教案详情
     */
    @GetMapping("/v2/{id}")
    public Result<LessonPlan> getById(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long id) {
        String token = authHeader.replace("Bearer ", "");
        jwtUtil.getUserIdFromToken(token); // 校验登录态
        return Result.success(planAgentService.getPlanById(id));
    }

    /**
     * V2: 教师编辑教案
     */
    @PutMapping("/v2/{id}")
    public Result<LessonPlan> update(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long id,
            @RequestBody LessonPlanUpdateRequest request) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        return Result.success(planAgentService.updatePlan(id, userId, request));
    }

    /**
     * V2: 删除教案
     */
    @DeleteMapping("/v2/{id}")
    public Result<Void> delete(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long id) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        planAgentService.deletePlan(id, userId);
        return Result.success();
    }
}
