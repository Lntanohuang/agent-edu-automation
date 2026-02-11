-- 智能教育平台数据库脚本
-- 数据库: edu_platform
-- 字符集: utf8mb4

CREATE DATABASE IF NOT EXISTS edu_platform 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE edu_platform;

-- ============================================
-- 1. 用户表 (users)
-- ============================================
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '加密密码',
    nickname VARCHAR(50) COMMENT '昵称',
    avatar_url VARCHAR(500) COMMENT '头像URL',
    email VARCHAR(100) COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    role ENUM('teacher', 'admin') DEFAULT 'teacher' COMMENT '角色',
    subjects JSON COMMENT '教授的学科列表 ["数学", "物理"]',
    status TINYINT DEFAULT 1 COMMENT '状态: 0-禁用, 1-正常',
    last_login_time TIMESTAMP NULL COMMENT '最后登录时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ============================================
-- 2. 对话表 (conversations)
-- ============================================
CREATE TABLE conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '对话ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    title VARCHAR(200) COMMENT '对话标题',
    context JSON COMMENT '上下文信息 {subject: "数学", grade: "初二"}',
    message_count INT DEFAULT 0 COMMENT '消息数量',
    status ENUM('active', 'archived') DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_updated_at (updated_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话表';

-- ============================================
-- 3. 消息表 (messages)
-- ============================================
CREATE TABLE messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
    conversation_id BIGINT NOT NULL COMMENT '对话ID',
    role ENUM('user', 'assistant', 'system') NOT NULL COMMENT '角色',
    content TEXT NOT NULL COMMENT '消息内容',
    tokens_used INT COMMENT '消耗的token数',
    metadata JSON COMMENT '元数据 {model: "gpt-4", temperature: 0.7}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息表';

-- ============================================
-- 4. 教案表 (lesson_plans)
-- ============================================
CREATE TABLE lesson_plans (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '教案ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    title VARCHAR(200) NOT NULL COMMENT '教案标题',
    subject VARCHAR(50) COMMENT '学科',
    grade VARCHAR(50) COMMENT '年级',
    topic VARCHAR(200) COMMENT '课题/主题',
    duration INT COMMENT '课时数',
    class_size INT COMMENT '班级人数',
    textbook_version VARCHAR(50) COMMENT '教材版本',
    difficulty VARCHAR(20) COMMENT '难度: 简单/中等/困难',
    objectives JSON COMMENT '教学目标 ["...", "..."]',
    key_points JSON COMMENT '教学重点 ["..."]',
    difficulties JSON COMMENT '教学难点 ["..."]',
    teaching_methods JSON COMMENT '教学方法 ["..."]',
    teaching_aids JSON COMMENT '教学用具 ["..."]',
    procedures JSON COMMENT '教学过程 [{stage, duration, content, activities, designIntent}]',
    homework TEXT COMMENT '作业布置',
    blackboard_design TEXT COMMENT '板书设计',
    reflection TEXT COMMENT '教学反思',
    resources JSON COMMENT '推荐资源 [{type, title, url}]',
    status ENUM('generated', 'saved', 'published') DEFAULT 'generated' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_user_id (user_id),
    INDEX idx_subject_grade (subject, grade),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教案表';

-- ============================================
-- 5. 批阅任务表 (grading_tasks)
-- ============================================
CREATE TABLE grading_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '任务ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    title VARCHAR(200) NOT NULL COMMENT '任务标题',
    subject VARCHAR(50) COMMENT '学科',
    grade VARCHAR(50) COMMENT '年级',
    type ENUM('essay', 'code', 'math', 'english', 'other') NOT NULL COMMENT '作业类型',
    rubric JSON COMMENT '评分标准 [{criteria, weight, description}]',
    max_score INT DEFAULT 100 COMMENT '满分',
    deadline TIMESTAMP NULL COMMENT '截止日期',
    total_submissions INT DEFAULT 0 COMMENT '提交总数',
    graded_count INT DEFAULT 0 COMMENT '已批阅数',
    avg_score DECIMAL(5,2) COMMENT '平均分',
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_type (type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批阅任务表';

-- ============================================
-- 6. 学生作业表 (submissions)
-- ============================================
CREATE TABLE submissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '提交ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    student_name VARCHAR(50) COMMENT '学生姓名',
    student_id VARCHAR(50) COMMENT '学号',
    content TEXT COMMENT '作业内容（文本）',
    file_url VARCHAR(500) COMMENT '附件URL',
    file_type VARCHAR(50) COMMENT '文件类型',
    overall_score INT COMMENT '总评分',
    overall_comment TEXT COMMENT '总评评语',
    strengths JSON COMMENT '优点 ["..."]',
    weaknesses JSON COMMENT '不足 ["..."]',
    suggestions JSON COMMENT '建议 ["..."]',
    criteria_scores JSON COMMENT '分项评分 [{criteriaId, score, comment}]',
    detailed_comments TEXT COMMENT '详细点评',
    metadata JSON COMMENT '元数据 {wordCount, spellingErrors, grammarErrors, plagiarismScore}',
    status ENUM('uploaded', 'grading', 'graded', 'failed') DEFAULT 'uploaded' COMMENT '状态',
    graded_at TIMESTAMP NULL COMMENT '批阅时间',
    graded_by ENUM('AI', 'teacher') DEFAULT 'AI' COMMENT '批阅人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_task_id (task_id),
    INDEX idx_student_id (student_id),
    INDEX idx_status (status),
    INDEX idx_graded_at (graded_at),
    FOREIGN KEY (task_id) REFERENCES grading_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生作业表';

-- ============================================
-- 7. 文件表 (files)
-- ============================================
CREATE TABLE files (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '文件ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    filename VARCHAR(255) COMMENT '存储文件名',
    original_name VARCHAR(255) COMMENT '原始文件名',
    url VARCHAR(500) COMMENT '访问URL',
    size BIGINT COMMENT '文件大小(字节)',
    mime_type VARCHAR(100) COMMENT 'MIME类型',
    type ENUM('image', 'document', 'video', 'audio') COMMENT '文件类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_user_id (user_id),
    INDEX idx_type (type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件表';

-- ============================================
-- 8. 系统配置表 (system_configs)
-- ============================================
CREATE TABLE system_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(500) COMMENT '描述',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    extend_field1 VARCHAR(255) DEFAULT NULL COMMENT '预留字段1',
    extend_field2 VARCHAR(255) DEFAULT NULL COMMENT '预留字段2',
    extend_field3 VARCHAR(255) DEFAULT NULL COMMENT '预留字段3',
    extend_field4 VARCHAR(255) DEFAULT NULL COMMENT '预留字段4',
    extend_field5 VARCHAR(255) DEFAULT NULL COMMENT '预留字段5',

    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- ============================================
-- 插入默认管理员账号 (密码: admin123)
-- ============================================
-- 密码: admin123 (BCrypt)
INSERT INTO users (username, password, nickname, role, subjects, status) VALUES 
('admin', '$2a$10$7JB720yubVS0vunZvHjN5e9FQ67gYzqH4LZGJxqjfzD9Fu5xPjd/.', '管理员', 'admin', '["全部"]', 1);

-- 插入默认教师账号 (密码: teacher123)
INSERT INTO users (username, password, nickname, role, subjects, status) VALUES 
('teacher001', '$2a$10$XQm6DFrT1OUbO7OuJaVRleQmtL6PjFvXbMdG.XD9VoTK3eI5MJRIe', '王老师', 'teacher', '["数学", "物理"]', 1);

-- 插入测试账号 (密码: test123)
INSERT INTO users (username, password, nickname, role, subjects, status) VALUES 
('test', '$2a$10$yQnS.zPcCfHYLwD3yd8wJOwdeFLYJQLWXdF8oK.qYY4EjvWpPdlx2', '测试用户', 'teacher', '["语文"]', 1);

-- ============================================
-- 插入系统配置
-- ============================================
INSERT INTO system_configs (config_key, config_value, description) VALUES
('ai.model.default', 'gpt-4', '默认AI模型'),
('ai.temperature', '0.7', 'AI温度参数'),
('ai.max_tokens', '2000', '最大token数'),
('file.max_size', '52428850', '文件最大大小(50MB)'),
('grading.batch_size', '10', '批量批阅并发数');
