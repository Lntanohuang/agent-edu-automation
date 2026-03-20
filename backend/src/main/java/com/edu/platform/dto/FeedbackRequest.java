package com.edu.platform.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class FeedbackRequest {

    @NotBlank(message = "对话ID不能为空")
    private String conversationId;

    @NotBlank(message = "消息ID不能为空")
    private String messageId;

    @NotBlank(message = "评价不能为空")
    private String rating;

    private String comment;

    private String confidence;
}
