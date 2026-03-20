package com.edu.platform.repository;

import com.edu.platform.entity.Conversation;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ConversationRepository extends JpaRepository<Conversation, Long> {

    /**
     * 查询用户的对话列表（按更新时间倒序）
     */
    Page<Conversation> findByUserIdOrderByUpdatedAtDesc(Long userId, Pageable pageable);

    /**
     * 查询用户的活跃对话
     */
    List<Conversation> findByUserIdAndStatusOrderByUpdatedAtDesc(Long userId, Conversation.Status status);

    /**
     * 增加消息计数
     */
    @Modifying
    @Query("UPDATE Conversation c SET c.messageCount = c.messageCount + 1 WHERE c.id = :id")
    void incrementMessageCount(@Param("id") Long id);

    /**
     * 更新对话标题
     */
    @Modifying
    @Query("UPDATE Conversation c SET c.title = :title WHERE c.id = :id")
    void updateTitle(@Param("id") Long id, @Param("title") String title);
}
