package com.edu.platform.controller;

import com.edu.platform.common.Result;
import com.edu.platform.dto.*;
import com.edu.platform.service.AuthService;
import com.edu.platform.util.JwtUtil;
import io.github.resilience4j.ratelimiter.annotation.RateLimiter;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 认证控制器
 * 路径前缀: /api/auth
 */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final JwtUtil jwtUtil;

    /**
     * 用户登录
     * 
     * POST /api/auth/login
     * 
     * 请求示例:
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
     * 错误示例 (密码错误):
     * {
     *   "username": "teacher001",
     *   "password": "wrongpassword"
     * }
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "success",
     *   "data": {
     *     "token": "eyJhbGciOiJIUzI1NiIs...",
     *     "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
     *     "expiresIn": 7200000,
     *     "user": {
     *       "id": 2,
     *       "username": "teacher001",
     *       "nickname": "王老师",
     *       "avatar": null,
     *       "role": "teacher",
     *       "subjects": ["数学", "物理"]
     *     }
     *   },
     *   "timestamp": "2024-01-15T10:30:00"
     * }
     * 
     * 错误响应:
     * {
     *   "code": 401,
     *   "message": "用户名或密码错误",
     *   "data": null,
     *   "timestamp": "2024-01-15T10:30:00"
     * }
     */
    @RateLimiter(name = "authApi")
    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return Result.success(authService.login(request));
    }

    /**
     * 用户注册
     * 
     * POST /api/auth/register
     * 
     * 请求示例:
     * {
     *   "username": "zhangsan",
     *   "password": "zhangsan123",
     *   "nickname": "张老师",
     *   "email": "zhangsan@school.com",
     *   "phone": "13800138000",
     *   "subjects": ["语文", "历史"]
     * }
     * 
     * 最小示例 (只传必填项):
     * {
     *   "username": "lisi",
     *   "password": "lisi123456",
     *   "nickname": "李老师"
     * }
     * 
     * 错误示例 (用户名已存在):
     * {
     *   "username": "teacher001",
     *   "password": "password123"
     * }
     * 
     * 错误示例 (密码太短):
     * {
     *   "username": "wangwu",
     *   "password": "123"
     * }
     * 
     * 成功响应: 同登录接口
     */
    @PostMapping("/register")
    public Result<LoginResponse> register(@Valid @RequestBody RegisterRequest request) {
        return Result.success(authService.register(request));
    }

    /**
     * 刷新令牌
     * 
     * POST /api/auth/refresh
     * 
     * 请求示例:
     * {
     *   "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
     * }
     * 
     * 成功响应: 同登录接口，返回新的 token 和 refreshToken
     * 
     * 错误响应 (令牌过期):
     * {
     *   "code": 401,
     *   "message": "刷新令牌无效或已过期"
     * }
     */
    @RateLimiter(name = "authApi")
    @PostMapping("/refresh")
    public Result<LoginResponse> refreshToken(@Valid @RequestBody RefreshTokenRequest request) {
        return Result.success(authService.refreshToken(request));
    }

    /**
     * 获取当前登录用户信息
     * 
     * GET /api/auth/me
     * 
     * 请求头:
     * Authorization: Bearer {token}
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "success",
     *   "data": {
     *     "id": 2,
     *     "username": "teacher001",
     *     "nickname": "王老师",
     *     "avatar": null,
     *     "role": "teacher",
     *     "subjects": ["数学", "物理"]
     *   }
     * }
     * 
     * 错误响应 (未登录):
     * {
     *   "code": 401,
     *   "message": "请先登录"
     * }
     */
    @GetMapping("/me")
    public Result<LoginResponse.UserInfo> getCurrentUser(
            @RequestHeader("Authorization") String authHeader) {
        String token = authHeader.replace("Bearer ", "");
        Long userId = jwtUtil.getUserIdFromToken(token);
        return Result.success(authService.getCurrentUser(userId));
    }

    /**
     * 退出登录
     * 
     * POST /api/auth/logout
     * 
     * 请求头:
     * Authorization: Bearer {token}
     * 
     * 成功响应:
     * {
     *   "code": 200,
     *   "message": "退出成功",
     *   "data": null
     * }
     */
    @PostMapping("/logout")
    public Result<Void> logout(@RequestHeader("Authorization") String authHeader) {
        // 实际项目中可以在这里将 token 加入黑名单（Redis）
        // 或者让前端删除 token
        return Result.success("退出成功", null);
    }
}
