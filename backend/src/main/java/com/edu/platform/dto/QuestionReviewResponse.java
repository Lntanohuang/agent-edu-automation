package com.edu.platform.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class QuestionReviewResponse {
    private Long draftId;
    private String reviewStatus;
    private Long importedCount;
    private String message;
}
