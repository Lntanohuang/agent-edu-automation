package com.edu.platform.controller;

import com.edu.platform.common.Result;
import com.edu.platform.dto.PlanAgentGenerateRequest;
import com.edu.platform.dto.PlanAgentGenerateResponse;
import com.edu.platform.service.PlanAgentService;
import com.edu.platform.util.JwtUtil;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/plan-agent")
@RequiredArgsConstructor
public class PlanAgentController {

    private final PlanAgentService planAgentService;
    private final JwtUtil jwtUtil;

    @PostMapping("/generate")
    public Result<PlanAgentGenerateResponse> generate(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody PlanAgentGenerateRequest request) {
        // 保持与现有接口一致：校验并解析登录态
        String token = authHeader.replace("Bearer ", "");
        jwtUtil.getUserIdFromToken(token);
        return Result.success(planAgentService.generatePlan(request));
    }
}
