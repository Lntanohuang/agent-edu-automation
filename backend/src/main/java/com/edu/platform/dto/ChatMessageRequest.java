package com.edu.platform.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.Map;

/**
 * 发送消息请求 DTO
 * 
 * 新对话示例:
 * {
 *   "message": "如何设计一堂生动有趣的数学课？",
 *   "context": {
 *     "subject": "数学",
 *     "grade": "初二"
 *   }
 * }
 * 
 * 继续对话示例:
 * {
 *   "message": "能具体说说导入环节怎么设计吗？",
 *   "conversationId": "1",
 *   "context": {
 *     "subject": "数学",
 *     "grade": "初二"
 *   }
 * }
 * 
 * 错误示例 (消息为空):
 * {
 *   "message": "",
 *   "conversationId": "1"
 * }
 * 
 * 错误示例 (消息太长):
 * {
 *   "message": "...超过4000字符..."
 * }
 */
@Data
public class ChatMessageRequest {

    @NotBlank(message = "消息内容不能为空")
    @Size(max = 4000, message = "消息内容不能超过4000字符")
    private String message;

    /**
     * 对话ID，为空则创建新对话
     */
    private Long conversationId;

    /**
     * 上下文信息
     */
    private Map<String, String> context;
}
