"""RAG 提示词模板 — 分层架构支持 Prefix Caching。

LLM 推理时，system prompt 的前缀如果与上次调用相同，
可以复用 KV cache，降低推理延迟和成本。

策略：
  Layer 0 (角色+核心规则) 固定在前，供 LLM KV-cache 复用。
  Layer 1 (意图特化) 根据 intent 动态追加。
  Layer 2 (skill/附加指令) 最后追加。
"""

# ── Layer 0: 角色定义（固定前缀，所有请求共享，可被 LLM prefix cache） ──
_ROLE_PREFIX = """你是法学院「劳动与社会保障法」课程的 AI 教学助手。

核心规则:
1. 只使用检索到的材料回答，严禁编造法条、案例或司法解释。
2. 信息不足时明确告知"检索到的材料未涵盖该问题"，并给出 1-2 个自学方向。
3. 每个回答必须包含「依据来源」，格式: 「《法律名》第X条」或「文件: xxx」。
4. 回答结构: 结论 → 法律依据 → 实务要点 → 拓展思考(1-2题)。

重要边界: 你只提供法律知识教学，不提供具体法律咨询意见。涉及"我应该怎么告/能不能打赢/该怎么维权"类问题，请建议咨询执业律师。"""

# 向后兼容别名
_RAG_FIXED_PREFIX = _ROLE_PREFIX

# ── Layer 1: 意图特化指令（根据检测到的问题意图动态追加） ──
_INTENT_INSTRUCTIONS: dict[str, str] = {
    "law_article": """当前问题涉及具体法条查询。要求:
- 完整引用法条原文，不可省略或改写任何文字
- 如法条有多款，逐款解读关键要件和适用条件
- 指出该条的常见误读或易混淆之处
- 如涉及交叉引用（"依照本法第X条"），一并解读被引用条文""",

    "concept_explain": """当前问题是法律概念解释类。要求:
- 先用一句话给出准确定义
- 通过正例和反例对比辨析（例如: "属于经济补偿的情形 vs 不属于的情形"）
- 关联 1-2 个易混淆的相近概念（例如: 经济补偿金 vs 赔偿金 vs 违约金）
- 说明该概念在实务中的判断标准""",

    "case_lookup": """当前问题涉及案例分析。要求:
- 先提炼裁判要旨（一句话概括法院核心观点）
- 还原争议焦点和双方主张
- 分析法院的推理逻辑和适用法条
- 指出该案对教学的启示价值""",

    "general": """当前问题较为宽泛或意图不明确。要求:
- 如果能判断用户大致方向，直接回答并在末尾追问以确认理解是否正确
- 如果完全无法判断，给出 2-3 个可能的问题方向供用户选择
- 保持简洁，不要过度展开""",
}


def build_rag_system_prompt(
    skill_name: str = "",
    additional_instructions: str = "",
    intent: str | None = None,
) -> str:
    """构建分层 RAG system prompt。

    Layer 0 (角色+核心规则) 固定在前，供 LLM KV-cache 复用。
    Layer 1 (意图特化) 根据 intent 动态追加。
    Layer 2 (skill/附加指令) 最后追加。

    Args:
        skill_name: 当前激活的技能名称。
        additional_instructions: 额外补充指令。
        intent: 问题意图，用于选择 Layer 1 指令。
    """
    parts = [_ROLE_PREFIX]

    # Layer 1: intent-specific instructions
    if intent and intent in _INTENT_INSTRUCTIONS:
        parts.append(_INTENT_INSTRUCTIONS[intent])

    # Layer 2: skill-specific / additional
    if skill_name:
        parts.append(f"当前使用技能: {skill_name}")
    if additional_instructions:
        parts.append(additional_instructions)

    return "\n\n".join(parts)


# 向后兼容别名
DEFAULT_RAG_SYSTEM_PROMPT = _ROLE_PREFIX
