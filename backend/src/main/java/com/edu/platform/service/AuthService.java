package com.edu.platform.service;

import com.alibaba.fastjson2.JSON;
import com.edu.platform.common.BusinessException;
import com.edu.platform.dto.*;
import com.edu.platform.entity.User;
import com.edu.platform.repository.UserRepository;
import com.edu.platform.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;

    /**
     * 用户登录
     */
    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new BusinessException(401, "用户名或密码错误"));

        if (user.getStatus() != 1) {
            throw new BusinessException(403, "账号已被禁用");
        }

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BusinessException(401, "用户名或密码错误");
        }

        // 更新最后登录时间
        user.setLastLoginTime(LocalDateTime.now());
        userRepository.save(user);

        // 生成 Token
        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole().name());
        String refreshToken = jwtUtil.generateRefreshToken(user.getId());

        // 解析 subjects
        List<String> subjects = parseSubjects(user.getSubjects());

        return LoginResponse.builder()
                .token(token)
                .refreshToken(refreshToken)
                .expiresIn(jwtUtil.getExpiration())
                .user(LoginResponse.UserInfo.builder()
                        .id(user.getId())
                        .username(user.getUsername())
                        .nickname(user.getNickname())
                        .avatar(user.getAvatarUrl())
                        .role(user.getRole().name())
                        .subjects(subjects)
                        .build())
                .build();
    }

    /**
     * 用户注册
     */
    @Transactional
    public LoginResponse register(RegisterRequest request) {
        // 检查用户名是否已存在
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new BusinessException(400, "用户名已存在");
        }

        // 检查邮箱是否已存在
        if (request.getEmail() != null && userRepository.existsByEmail(request.getEmail())) {
            throw new BusinessException(400, "邮箱已被注册");
        }

        // 创建新用户
        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setNickname(request.getNickname() != null ? request.getNickname() : request.getUsername());
        user.setEmail(request.getEmail());
        user.setPhone(request.getPhone());
        user.setRole(User.Role.teacher);
        user.setSubjects(request.getSubjects() != null ? JSON.toJSONString(request.getSubjects()) : "[]");
        user.setStatus(1);

        userRepository.save(user);

        // 生成 Token
        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole().name());
        String refreshToken = jwtUtil.generateRefreshToken(user.getId());

        return LoginResponse.builder()
                .token(token)
                .refreshToken(refreshToken)
                .expiresIn(jwtUtil.getExpiration())
                .user(LoginResponse.UserInfo.builder()
                        .id(user.getId())
                        .username(user.getUsername())
                        .nickname(user.getNickname())
                        .avatar(user.getAvatarUrl())
                        .role(user.getRole().name())
                        .subjects(request.getSubjects())
                        .build())
                .build();
    }

    /**
     * 刷新 Token
     */
    public LoginResponse refreshToken(RefreshTokenRequest request) {
        // 验证刷新令牌
        if (!jwtUtil.validateToken(request.getRefreshToken())) {
            throw new BusinessException(401, "刷新令牌无效或已过期");
        }

        Long userId = jwtUtil.getUserIdFromToken(request.getRefreshToken());
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(401, "用户不存在"));

        if (user.getStatus() != 1) {
            throw new BusinessException(403, "账号已被禁用");
        }

        // 生成新的 Token
        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole().name());
        String refreshToken = jwtUtil.generateRefreshToken(user.getId());

        List<String> subjects = parseSubjects(user.getSubjects());

        return LoginResponse.builder()
                .token(token)
                .refreshToken(refreshToken)
                .expiresIn(jwtUtil.getExpiration())
                .user(LoginResponse.UserInfo.builder()
                        .id(user.getId())
                        .username(user.getUsername())
                        .nickname(user.getNickname())
                        .avatar(user.getAvatarUrl())
                        .role(user.getRole().name())
                        .subjects(subjects)
                        .build())
                .build();
    }

    /**
     * 获取当前用户信息
     */
    @Cacheable(value = "user", key = "#userId")
    public LoginResponse.UserInfo getCurrentUser(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(404, "用户不存在"));

        List<String> subjects = parseSubjects(user.getSubjects());

        return LoginResponse.UserInfo.builder()
                .id(user.getId())
                .username(user.getUsername())
                .nickname(user.getNickname())
                .avatar(user.getAvatarUrl())
                .role(user.getRole().name())
                .subjects(subjects)
                .build();
    }

    /**
     * 解析学科 JSON
     */
    private List<String> parseSubjects(String subjectsJson) {
        if (subjectsJson == null || subjectsJson.isEmpty()) {
            return List.of();
        }
        try {
            return JSON.parseArray(subjectsJson, String.class);
        } catch (Exception e) {
            return List.of();
        }
    }
}
