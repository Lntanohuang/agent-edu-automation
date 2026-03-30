package com.edu.platform.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PlanAgentV2GenerateResponse {

    private Boolean success;
    private String message;
    private Long planId;
    private Map<String, Object> semesterPlan;
    /** Agent 元数据：skill_status, conflicts, data_gaps, merge_priority, total_time_ms */
    private Map<String, Object> agentMeta;
}
