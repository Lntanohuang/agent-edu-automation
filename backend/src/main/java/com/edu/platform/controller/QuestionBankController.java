package com.edu.platform.controller;

import com.edu.platform.common.Result;
import com.edu.platform.dto.QuestionGenerateRequest;
import com.edu.platform.dto.QuestionGenerateResponse;
import com.edu.platform.dto.QuestionReviewRequest;
import com.edu.platform.dto.QuestionReviewResponse;
import com.edu.platform.service.QuestionBankService;
import com.edu.platform.util.JwtUtil;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/question-bank")
@RequiredArgsConstructor
public class QuestionBankController {

    private final QuestionBankService questionBankService;
    private final JwtUtil jwtUtil;

    @PostMapping("/generate")
    public Result<QuestionGenerateResponse> generate(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody QuestionGenerateRequest request) {
        Long userId = parseUserId(authHeader);
        return Result.success(questionBankService.generate(userId, request));
    }

    @GetMapping("/drafts")
    public Result<Page<Map<String, Object>>> listDrafts(
            @RequestHeader("Authorization") String authHeader,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        Long userId = parseUserId(authHeader);
        Pageable pageable = PageRequest.of(page - 1, size);
        return Result.success(questionBankService.listDrafts(userId, pageable));
    }

    @GetMapping("/drafts/{draftId}")
    public Result<Map<String, Object>> getDraftDetail(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long draftId) {
        Long userId = parseUserId(authHeader);
        return Result.success(questionBankService.getDraftDetail(userId, draftId));
    }

    @PostMapping("/drafts/{draftId}/review")
    public Result<QuestionReviewResponse> reviewDraft(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long draftId,
            @Valid @RequestBody QuestionReviewRequest request) {
        Long userId = parseUserId(authHeader);
        return Result.success(questionBankService.reviewDraft(userId, draftId, request));
    }

    @GetMapping("/items")
    public Result<Page<Map<String, Object>>> listItems(
            @RequestHeader("Authorization") String authHeader,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        Long userId = parseUserId(authHeader);
        Pageable pageable = PageRequest.of(page - 1, size);
        return Result.success(questionBankService.listQuestionBank(userId, pageable));
    }

    private Long parseUserId(String authHeader) {
        String token = authHeader.replace("Bearer ", "");
        return jwtUtil.getUserIdFromToken(token);
    }
}
