package com.edu.platform.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
@Builder
public class QuestionGenerateResponse {
    private Long draftId;
    private String reviewStatus;
    private String message;
    private String generationMode;
    private Integer questionCount;
    private Map<String, Object> questionSet;
    private List<String> bookLabels;
    private List<String> sources;
    private List<String> validationNotes;
}
