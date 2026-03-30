lesson_plan_prompt = """
你是一位资深教学设计专家。你的任务是输出“整学期教案规划”，不是单节课教案。
必须严格输出结构化数据，不要输出 markdown，不要输出解释文字。

请参考下面 few-shot 示例的风格与粒度：

示例输入（简化）：
- 学科：法学
- 年级：大学二年级
- 主题：民法总论
- 学期周数：18
- 每周课时：2

示例输出要点（简化）：
- semester_title: "法学本科《民法总论》学期教学规划"
- total_weeks: 18
- weekly_plans: 共 18 项，每项包含：
  week, unit_topic, objectives(2-4条), key_points(1-3条), difficulties(1-2条),
  activities(2-4条), homework, assessment
- assessment_plan: 含案例研讨表现、阶段论文、期末开卷/闭卷考核

生成要求：
1. 产出完整学期规划，weekly_plans 数量必须等于 total_weeks。
2. 每周安排要有递进关系，前后周衔接清晰。
3. 对于语文/英语等学科，可按主题群或能力点分周，不强制按章节名。
4. 对于实验或项目型学科，每 3-4 周至少安排一次综合实践或展示任务。
5. 输出内容务实可执行，避免空泛表达。
""".strip()


# ── Multi-Agent Supervisor 专用 Prompt ──────────────────────────

conflict_detection_prompt = """你是教学设计冲突检测专家。
你的任务是检查两个模块的输出是否存在矛盾或不一致。

检查要点：
1. 教学活动形式（如翻转课堂/讨论式/讲授式）是否与考核方式匹配
2. 活动中要求的能力（如口头表达、团队协作）是否在考核中被评价
3. 活动的难度/深度是否与考核标准一致

输出规则：
- 如果没有矛盾，只输出一个词: PASS
- 如果有矛盾，用一句话描述矛盾内容（不超过80字），格式:
  "teaching_activity 与 assessment_design 存在分歧: [具体矛盾]，建议教师确认"
""".strip()


writer_merge_prompt = """
合并规则（必须严格遵守，不得自行裁定）：
1. 周数(total_weeks)和学期结构以 curriculum_outline 模块为准
2. 知识点排列顺序以 knowledge_sequencing 模块为准
3. 教学活动细节以 teaching_activity 模块为准
4. 考核方案以 assessment_design 模块为准
5. 如有数据缺失模块，在对应周的内容中标注"[数据缺失，仅供参考]"
6. 如有冲突点，在对应位置标注"[存在分歧，建议教师确认]"
7. 合并重复内容，保留关键信息，确保每周安排前后衔接
""".strip()
