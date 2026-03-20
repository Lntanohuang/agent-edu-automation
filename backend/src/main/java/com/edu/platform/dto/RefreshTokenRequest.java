package com.edu.platform.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 刷新令牌请求 DTO
 * 
 * 测试 JSON:
 * {
 *   "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
 * }
 * 
 * 错误示例 (空令牌):
 * {
 *   "refreshToken": ""
 * }
 */
@Data
public class RefreshTokenRequest {

    @NotBlank(message = "刷新令牌不能为空")
    private String refreshToken;
}
