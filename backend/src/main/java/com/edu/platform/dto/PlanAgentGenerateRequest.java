package com.edu.platform.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class PlanAgentGenerateRequest {

    @NotBlank(message = "学科不能为空")
    @Size(max = 50, message = "学科长度不能超过50")
    private String subject;

    private String grade = "无";
    private String topic = "课程主题";
    private Integer totalWeeks = 18;
    private Integer lessonsPerWeek = 2;
    private Integer classSize = 40;
    private String courseType = "专业必修";
    private Integer credits = 3;
    private String assessmentMode = "期末闭卷 + 平时成绩";
    private String teachingGoals = "掌握本课核心知识与基本应用";
    private String requirements = "无";
    private String textbookVersion = "通用版";
    private String difficulty = "中等";
    private String traceProjectName;
}
