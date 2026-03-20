package com.edu.platform.config;

import com.edu.platform.entity.User;
import com.edu.platform.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) {
        // 初始化管理员账号
        initUser("admin", "admin123", "管理员", User.Role.admin, "[\"全部\"]");
        
        // 初始化教师账号
        initUser("teacher001", "teacher123", "王老师", User.Role.teacher, "[\"数学\", \"物理\"]");
        
        // 初始化测试账号
        initUser("test", "test123", "测试用户", User.Role.teacher, "[\"语文\"]");
        
        log.info("测试数据初始化完成");
    }
    
    private void initUser(String username, String password, String nickname, 
                         User.Role role, String subjects) {
        if (userRepository.existsByUsername(username)) {
            log.info("用户 {} 已存在，跳过初始化", username);
            return;
        }
        
        User user = new User();
        user.setUsername(username);
        user.setPassword(passwordEncoder.encode(password));  // 正确加密
        user.setNickname(nickname);
        user.setRole(role);
        user.setSubjects(subjects);
        user.setStatus(1);
        
        userRepository.save(user);
        log.info("创建用户: {} / 密码: {}", username, password);
    }
}
