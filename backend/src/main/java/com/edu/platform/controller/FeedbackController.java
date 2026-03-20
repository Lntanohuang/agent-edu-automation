package com.edu.platform.controller;

import com.edu.platform.common.Result;
import com.edu.platform.dto.FeedbackRequest;
import com.edu.platform.entity.AiFeedback;
import com.edu.platform.service.FeedbackService;
import com.edu.platform.util.JwtUtil;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/feedback")
@RequiredArgsConstructor
public class FeedbackController {

    private final FeedbackService feedbackService;
    private final JwtUtil jwtUtil;

    @PostMapping
    public Result<Map<String, Object>> submit(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody FeedbackRequest request) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        AiFeedback feedback = feedbackService.submit(userId, request);
        return Result.success(Map.of("feedbackId", feedback.getId()));
    }
}
