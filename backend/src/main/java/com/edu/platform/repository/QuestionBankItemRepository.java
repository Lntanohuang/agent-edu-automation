package com.edu.platform.repository;

import com.edu.platform.entity.QuestionBankItem;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface QuestionBankItemRepository extends JpaRepository<QuestionBankItem, Long> {

    long countByDraftId(Long draftId);

    List<QuestionBankItem> findByDraftIdOrderByIdAsc(Long draftId);

    Page<QuestionBankItem> findByUserIdAndStatusOrderByCreatedAtDesc(Long userId, QuestionBankItem.Status status, Pageable pageable);
}
