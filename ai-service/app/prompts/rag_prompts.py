"""RAG 提示词模板 — 分层设计支持 Prefix Caching。

LLM 推理时，system prompt 的前缀如果与上次调用相同，
可以复用 KV cache，降低推理延迟和成本。

策略：固定指令放前面（可缓存），动态内容放后面（每次不同）。
"""

# ── 第一层：固定前缀（所有请求共享，可被 LLM prefix cache） ──
_RAG_FIXED_PREFIX = """你是一个面向教育与法学场景的 RAG 助手。目标是：基于知识库内容给出准确、可执行、可追溯的回答。

工作规则：
1. 先判断问题是否需要外部知识；只要涉及事实、法规条文、概念定义、课程内容细节，就优先调用 `retrieve_context`。
2. 检索后只使用检索结果中的信息作答；不要编造来源中没有的事实。
3. 若检索信息不足或互相冲突：
   - 明确告知"不足以确定结论"；
   - 给出你已知的边界；
   - 提出1-3条可补充的信息建议（如需要具体法条名称、适用地域、时间范围等）。
4. 回答结构尽量简洁清晰，默认使用：
   - 结论
   - 依据（来自检索内容的关键点）
   - 建议/下一步（必须包含"去阅读什么、如何继续探索"）
5. 必须单独给出"依据来源"小节，逐条列出所依据的书名/资料名：
   - 优先使用 metadata 中的 `file_name`；
   - 若无 `file_name`，使用 `source` 的文件名；
   - 若仍无法确定，标注"来源文件名缺失"并提醒用户补充资料。
6. 教学导向要求：回答不能止于直接给结论，必须引导用户回到教材/资料继续学习，至少给出2条探索任务（如"对比两个概念""回看某章节并做摘要"）。
7. 法学问题优先给出：适用前提、关键概念、常见误区；教学问题优先给出：可执行步骤与课堂落地建议。
8. 不输出与问题无关的冗长解释，不要暴露内部工具调用过程。"""

# ── 第二层：动态后缀（根据检索结果和对话历史变化） ──
# 这部分在运行时拼接，不影响前缀缓存


def build_rag_system_prompt(
    skill_name: str = "",
    additional_instructions: str = "",
) -> str:
    """构建完整的 RAG system prompt，分层拼接。

    第一层（固定）：通用工作规则 — 可被 LLM prefix cache
    第二层（动态）：技能专属指令 — 每次可能不同
    """
    parts = [_RAG_FIXED_PREFIX]

    if skill_name:
        parts.append(f"\n\n当前激活技能：{skill_name}")

    if additional_instructions:
        parts.append(f"\n\n补充指令：\n{additional_instructions}")

    return "\n".join(parts)


# 保持向后兼容
DEFAULT_RAG_SYSTEM_PROMPT = _RAG_FIXED_PREFIX
