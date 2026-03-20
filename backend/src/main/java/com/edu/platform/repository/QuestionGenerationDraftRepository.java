package com.edu.platform.repository;

import com.edu.platform.entity.QuestionGenerationDraft;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface QuestionGenerationDraftRepository extends JpaRepository<QuestionGenerationDraft, Long> {

    Page<QuestionGenerationDraft> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);

    Optional<QuestionGenerationDraft> findByIdAndUserId(Long id, Long userId);
}
