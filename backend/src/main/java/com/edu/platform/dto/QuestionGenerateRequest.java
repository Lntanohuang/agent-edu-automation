package com.edu.platform.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class QuestionGenerateRequest {

    @NotBlank(message = "学科不能为空")
    private String subject = "大学计算机";

    private String topic = "教材重点章节";

    private List<String> textbookScope = new ArrayList<>();

    @Min(value = 1, message = "题量不能小于 1")
    @Max(value = 50, message = "题量不能超过 50")
    private Integer questionCount = 10;

    private List<String> questionTypes = new ArrayList<>(List.of("单选题", "多选题", "判断题", "填空题", "简答题", "编程题"));

    @Valid
    private DifficultyDistribution difficultyDistribution = new DifficultyDistribution();

    private String outputMode = "practice";

    @Min(value = 1, message = "总分不能小于 1")
    @Max(value = 300, message = "总分不能超过 300")
    private Integer totalScore = 100;

    private Boolean includeAnswer = true;

    private Boolean includeExplanation = true;

    private Boolean requireSourceCitation = true;

    @Data
    public static class DifficultyDistribution {
        @Min(value = 0, message = "简单题比例不能小于 0")
        @Max(value = 100, message = "简单题比例不能超过 100")
        private Integer easy = 20;

        @Min(value = 0, message = "中等题比例不能小于 0")
        @Max(value = 100, message = "中等题比例不能超过 100")
        private Integer medium = 60;

        @Min(value = 0, message = "困难题比例不能小于 0")
        @Max(value = 100, message = "困难题比例不能超过 100")
        private Integer hard = 20;
    }
}
