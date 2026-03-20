package com.edu.platform.repository;

import com.edu.platform.entity.Message;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MessageRepository extends JpaRepository<Message, Long> {

    /**
     * 查询对话的所有消息（按时间正序）
     */
    List<Message> findByConversationIdOrderByCreatedAtAsc(Long conversationId);

    /**
     * 查询对话的消息数量
     */
    long countByConversationId(Long conversationId);

    /**
     * 删除对话的所有消息
     */
    void deleteByConversationId(Long conversationId);

    /**
     * 查询最近的 N 条消息（用于上下文）
     */
    @Query(value = "SELECT * FROM messages WHERE conversation_id = :conversationId ORDER BY created_at DESC LIMIT :limit", nativeQuery = true)
    List<Message> findRecentMessages(@Param("conversationId") Long conversationId, @Param("limit") int limit);
}
