package com.edu.platform.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.Map;

@Data
public class QuestionReviewRequest {

    @NotBlank(message = "审核动作不能为空")
    private String action;

    private String reviewNote;

    private Map<String, Object> editedQuestionSet;
}
