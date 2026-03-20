package com.edu.platform.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 登录请求 DTO
 * 
 * 测试 JSON:
 * {
 *   "username": "teacher001",
 *   "password": "teacher123"
 * }
 * 
 * 管理员登录:
 * {
 *   "username": "admin",
 *   "password": "admin123"
 * }
 * 
 * 错误示例 (密码太短):
 * {
 *   "username": "test",
 *   "password": "123"
 * }
 */
@Data
public class LoginRequest {

    @NotBlank(message = "用户名不能为空")
    @Size(min = 3, max = 50, message = "用户名长度必须在3-50之间")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 100, message = "密码长度必须在6-100之间")
    private String password;
}
