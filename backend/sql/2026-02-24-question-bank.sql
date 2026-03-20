USE edu_platform;

CREATE TABLE IF NOT EXISTS question_generation_drafts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '草稿ID',
    user_id BIGINT NOT NULL COMMENT '教师用户ID',
    title VARCHAR(200) NOT NULL COMMENT '草稿标题',
    subject VARCHAR(50) NOT NULL COMMENT '学科',
    topic VARCHAR(200) COMMENT '主题',
    textbook_scope JSON COMMENT '教材范围标签',
    generation_mode ENUM('practice', 'paper') DEFAULT 'practice' COMMENT '生成模式: 练习/试卷',
    question_count INT DEFAULT 0 COMMENT '题目数量',
    total_score INT DEFAULT 100 COMMENT '总分',
    review_status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending' COMMENT '审核状态',
    ai_payload LONGTEXT COMMENT 'AI返回的结构化题目内容',
    review_note VARCHAR(500) COMMENT '审核备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_qgd_user_id (user_id),
    INDEX idx_qgd_status (review_status),
    INDEX idx_qgd_created_at (created_at),
    CONSTRAINT fk_qgd_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能出题草稿表';

CREATE TABLE IF NOT EXISTS question_bank_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '题目ID',
    draft_id BIGINT NOT NULL COMMENT '来源草稿ID',
    user_id BIGINT NOT NULL COMMENT '教师用户ID',
    subject VARCHAR(50) NOT NULL COMMENT '学科',
    question_type VARCHAR(50) NOT NULL COMMENT '题型',
    difficulty VARCHAR(20) COMMENT '难度',
    stem TEXT NOT NULL COMMENT '题干',
    options_json JSON COMMENT '选项',
    answer_text TEXT NOT NULL COMMENT '答案',
    explanation TEXT NOT NULL COMMENT '解析',
    knowledge_points JSON COMMENT '知识点',
    source_citations JSON COMMENT '出处引用',
    score DECIMAL(8,2) DEFAULT 0 COMMENT '分值',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '题目状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_qbi_user_id (user_id),
    INDEX idx_qbi_draft_id (draft_id),
    INDEX idx_qbi_subject (subject),
    INDEX idx_qbi_status (status),
    INDEX idx_qbi_created_at (created_at),
    CONSTRAINT fk_qbi_draft FOREIGN KEY (draft_id) REFERENCES question_generation_drafts(id) ON DELETE CASCADE,
    CONSTRAINT fk_qbi_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='题库题目表';
