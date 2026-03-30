package com.edu.platform.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "lesson_plans")
public class LessonPlan {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(length = 50)
    private String subject;

    @Column(length = 50)
    private String grade;

    @Column(length = 200)
    private String topic;

    private Integer duration;

    @Column(name = "class_size")
    private Integer classSize;

    @Column(name = "textbook_version", length = 50)
    private String textbookVersion;

    @Column(length = 20)
    private String difficulty;

    @Column(columnDefinition = "JSON")
    private String objectives;

    @Column(name = "key_points", columnDefinition = "JSON")
    private String keyPoints;

    @Column(columnDefinition = "JSON")
    private String difficulties;

    @Column(name = "teaching_methods", columnDefinition = "JSON")
    private String teachingMethods;

    @Column(name = "teaching_aids", columnDefinition = "JSON")
    private String teachingAids;

    @Column(columnDefinition = "JSON")
    private String procedures;

    @Column(columnDefinition = "TEXT")
    private String homework;

    @Column(name = "blackboard_design", columnDefinition = "TEXT")
    private String blackboardDesign;

    @Column(columnDefinition = "TEXT")
    private String reflection;

    @Column(columnDefinition = "JSON")
    private String resources;

    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    private Status status = Status.generated;

    /** V2: 完整的学期计划 JSON */
    @Column(name = "semester_plan_json", columnDefinition = "TEXT")
    private String semesterPlanJson;

    /** V2: Agent 元数据 JSON（降级/冲突信息） */
    @Column(name = "agent_meta_json", columnDefinition = "TEXT")
    private String agentMetaJson;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public enum Status {
        generated, saved, published
    }
}
