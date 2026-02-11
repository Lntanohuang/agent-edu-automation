package com.edu.platform.controller;

import com.edu.platform.common.Result;
import com.edu.platform.dto.*;
import com.edu.platform.service.ChatService;
import com.edu.platform.util.JwtUtil;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

/**
 * 智能问答控制器
 * 路径前缀: /api/chat
 */
@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;
    private final JwtUtil jwtUtil;

    /**
     * 发送消息
     * 
     * POST /api/chat/message
     * Authorization: Bearer {token}
     * 
     * 新对话请求示例:
     * {
     *   "message": "如何设计一堂生动有趣的数学课？",
     *   "context": {
     *     "subject": "数学",
     *     "grade": "初二"
     *   }
     * }
     * 
     * 继续对话请求示例:
     * {
     *   "message": "能具体说说导入环节怎么设计吗？",
     *   "conversationId": 1,
     *   "context": {
     *     "subject": "数学",
     *     "grade": "初二"
     *   }
     * }
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "success",
     *   "data": {
     *     "messageId": 100,
     *     "conversationId": 1,
     *     "content": "这是一个很好的教学问题！我建议您可以从以下几个方面考虑...",
     *     "role": "assistant",
     *     "timestamp": "2024-01-15T10:30:00",
     *     "tokens": 150
     *   }
     * }
     * 
     * 错误响应 (对话不存在):
     * {
     *   "code": 404,
     *   "message": "对话不存在"
     * }
     */
    @PostMapping("/message")
    public Result<ChatMessageResponse> sendMessage(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody ChatMessageRequest request) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        return Result.success(chatService.sendMessage(userId, request));
    }

    /**
     * 流式发送消息 (SSE)
     * 
     * GET /api/chat/stream?message=xxx&conversationId=1
     * Authorization: Bearer {token}
     * 
     * 响应: SSE 流
     * data: {"content": "这是", "done": false}
     * data: {"content": "回复", "done": false}
     * data: {"content": "内容", "done": true}
     * 
     * TODO: 实际项目中需要调用 AI 服务的流式接口
     */
    @GetMapping("/stream")
    public SseEmitter streamMessage(
            @RequestHeader("Authorization") String authHeader,
            @RequestParam String message,
            @RequestParam(required = false) Long conversationId) {
        
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        
        SseEmitter emitter = new SseEmitter(120000L); // 2分钟超时
        
        // TODO: 实现流式调用 AI 服务
        // 模拟流式响应
        new Thread(() -> {
            try {
                String[] words = "这是一个流式回复示例".split("");
                for (String word : words) {
                    emitter.send(SseEmitter.event()
                            .data("{\"content\": \"" + word + "\", \"done\": false}"));
                    Thread.sleep(100);
                }
                emitter.send(SseEmitter.event()
                        .data("{\"content\": \"\", \"done\": true}"));
                emitter.complete();
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        }).start();
        
        return emitter;
    }

    /**
     * 获取对话列表
     * 
     * GET /api/chat/conversations?page=1&size=20
     * Authorization: Bearer {token}
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "success",
     *   "data": {
     *     "list": [
     *       {
     *         "id": 1,
     *         "title": "如何设计数学课",
     *         "lastMessage": "谢谢你的建议",
     *         "messageCount": 12,
     *         "createdAt": "2024-01-15T10:00:00",
     *         "updatedAt": "2024-01-15T10:30:00"
     *       }
     *     ],
     *     "total": 45,
     *     "page": 1,
     *     "size": 20
     *   }
     * }
     */
    @GetMapping("/conversations")
    public Result<Page<ConversationDTO>> getConversations(
            @RequestHeader("Authorization") String authHeader,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        Pageable pageable = PageRequest.of(page - 1, size);
        return Result.success(chatService.getConversations(userId, pageable));
    }

    /**
     * 获取对话消息历史
     * 
     * GET /api/chat/conversations/{conversationId}/messages
     * Authorization: Bearer {token}
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "success",
     *   "data": [
     *     {
     *       "messageId": 1,
     *       "conversationId": 1,
     *       "content": "如何设计一堂生动有趣的数学课？",
     *       "role": "user",
     *       "timestamp": "2024-01-15T10:00:00",
     *       "tokens": null
     *     },
     *     {
     *       "messageId": 2,
     *       "conversationId": 1,
     *       "content": "这是一个很好的教学问题...",
     *       "role": "assistant",
     *       "timestamp": "2024-01-15T10:00:05",
     *       "tokens": 150
     *     }
     *   ]
     * }
     * 
     * 错误响应 (无权访问):
     * {
     *   "code": 403,
     *   "message": "无权访问该对话"
     * }
     */
    @GetMapping("/conversations/{conversationId}/messages")
    public Result<List<ChatMessageResponse>> getMessages(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long conversationId) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        return Result.success(chatService.getMessages(userId, conversationId));
    }

    /**
     * 删除对话
     * 
     * DELETE /api/chat/conversations/{conversationId}
     * Authorization: Bearer {token}
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "删除成功",
     *   "data": null
     * }
     * 
     * 错误响应 (对话不存在):
     * {
     *   "code": 404,
     *   "message": "对话不存在"
     * }
     */
    @DeleteMapping("/conversations/{conversationId}")
    public Result<Void> deleteConversation(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long conversationId) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        chatService.deleteConversation(userId, conversationId);
        return Result.success("删除成功", null);
    }

    /**
     * 清空对话消息
     * 
     * DELETE /api/chat/conversations/{conversationId}/messages
     * Authorization: Bearer {token}
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "清空成功",
     *   "data": null
     * }
     */
    @DeleteMapping("/conversations/{conversationId}/messages")
    public Result<Void> clearMessages(
            @RequestHeader("Authorization") String authHeader,
            @PathVariable Long conversationId) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        chatService.clearMessages(userId, conversationId);
        return Result.success("清空成功", null);
    }
}
