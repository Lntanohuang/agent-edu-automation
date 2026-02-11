package com.edu.platform.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 注册请求 DTO
 * 
 * 测试 JSON:
 * {
 *   "username": "zhangsan",
 *   "password": "zhangsan123",
 *   "nickname": "张老师",
 *   "email": "zhangsan@school.com",
 *   "phone": "13800138000",
 *   "subjects": ["语文", "历史"]
 * }
 * 
 * 最小示例:
 * {
 *   "username": "lisi",
 *   "password": "lisi123456",
 *   "nickname": "李老师"
 * }
 * 
 * 错误示例 (邮箱格式错误):
 * {
 *   "username": "wangwu",
 *   "password": "wangwu123",
 *   "email": "invalid-email"
 * }
 */
@Data
public class RegisterRequest {

    @NotBlank(message = "用户名不能为空")
    @Size(min = 3, max = 50, message = "用户名长度必须在3-50之间")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 100, message = "密码长度必须在6-100之间")
    private String password;

    @Size(max = 50, message = "昵称长度不能超过50")
    private String nickname;

    @Email(message = "邮箱格式不正确")
    private String email;

    private String phone;

    private List<String> subjects;
}
