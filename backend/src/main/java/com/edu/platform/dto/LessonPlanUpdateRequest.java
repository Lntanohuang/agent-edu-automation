package com.edu.platform.dto;

import lombok.Data;

@Data
public class LessonPlanUpdateRequest {

    private String title;
    private String subject;
    private String grade;
    private String topic;
    private Integer duration;
    private Integer classSize;
    private String textbookVersion;
    private String difficulty;
    private String status;
    private String homework;
    private String blackboardDesign;
    private String reflection;
    /** 教师编辑后的学期计划 JSON */
    private String semesterPlanJson;
}
