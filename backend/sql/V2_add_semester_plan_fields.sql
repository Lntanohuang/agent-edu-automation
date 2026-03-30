-- V2: 为 lesson_plans 表添加学期计划和 Agent 元数据字段
-- 用于 Multi-Agent Supervisor 教案生成功能

ALTER TABLE lesson_plans
    ADD COLUMN semester_plan_json TEXT COMMENT '完整的学期计划 JSON（AI 返回）' AFTER resources,
    ADD COLUMN agent_meta_json TEXT COMMENT 'Agent 元数据 JSON（降级/冲突信息）' AFTER semester_plan_json;
