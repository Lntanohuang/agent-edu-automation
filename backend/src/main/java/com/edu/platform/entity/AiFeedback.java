package com.edu.platform.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "ai_feedbacks")
public class AiFeedback {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "conversation_id", length = 100)
    private String conversationId;

    @Column(name = "message_id", length = 100)
    private String messageId;

    @Column(nullable = false, length = 20)
    private String rating;

    @Column(columnDefinition = "TEXT")
    private String comment;

    @Column(length = 50)
    private String confidence;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
