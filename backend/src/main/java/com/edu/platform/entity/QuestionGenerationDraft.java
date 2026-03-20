package com.edu.platform.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "question_generation_drafts")
public class QuestionGenerationDraft {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(nullable = false, length = 50)
    private String subject;

    @Column(length = 200)
    private String topic;

    @Column(name = "textbook_scope", columnDefinition = "JSON")
    private String textbookScope;

    @Enumerated(EnumType.STRING)
    @Column(name = "generation_mode", nullable = false, length = 20)
    private GenerationMode generationMode = GenerationMode.practice;

    @Column(name = "question_count")
    private Integer questionCount = 0;

    @Column(name = "total_score")
    private Integer totalScore = 100;

    @Enumerated(EnumType.STRING)
    @Column(name = "review_status", nullable = false, length = 20)
    private ReviewStatus reviewStatus = ReviewStatus.pending;

    @Column(name = "ai_payload", columnDefinition = "LONGTEXT")
    private String aiPayload;

    @Column(name = "review_note", length = 500)
    private String reviewNote;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public enum GenerationMode {
        practice, paper
    }

    public enum ReviewStatus {
        pending, approved, rejected
    }
}
