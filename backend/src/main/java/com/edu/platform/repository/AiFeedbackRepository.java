package com.edu.platform.repository;

import com.edu.platform.entity.AiFeedback;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface AiFeedbackRepository extends JpaRepository<AiFeedback, Long> {
    boolean existsByUserIdAndMessageId(Long userId, String messageId);
}
