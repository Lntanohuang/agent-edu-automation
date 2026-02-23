package com.edu.platform.dto;

import lombok.Builder;
import lombok.Data;

import java.util.Map;

@Data
@Builder
public class PlanAgentGenerateResponse {
    private Boolean success;
    private String message;
    private Map<String, Object> semesterPlan;
}
