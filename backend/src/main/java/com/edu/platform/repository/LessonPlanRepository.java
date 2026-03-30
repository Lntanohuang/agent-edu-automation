package com.edu.platform.repository;

import com.edu.platform.entity.LessonPlan;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface LessonPlanRepository extends JpaRepository<LessonPlan, Long> {

    /**
     * 查询用户的教案列表（按创建时间倒序）
     */
    List<LessonPlan> findByUserIdOrderByCreatedAtDesc(Long userId);

    /**
     * 分页查询用户的教案
     */
    Page<LessonPlan> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);
}
