from langchain.agents import create_agent

from app.llm.model_factory import ollama_qwen_llm
from app.prompts.rag_prompts import DEFAULT_RAG_SYSTEM_PROMPT
from app.tools.rag_tool import retrieve_context



# 1.law_article
# 用途：处理法条/条文/适用前提类问题
# 特点：强调精确依据、适用边界、注意事项
# 输出：结论 + 条文依据 + 探索任务
# 2.case_analysis
# 用途：处理案例/案情/裁判思路类问题
# 特点：按“事实-争点-规则适用-结论”组织
# 输出：案例分析结论 + 探索任务
# 3.law_explain
# 用途：处理法学概念解释、概念区别类问题
# 特点：强调定义、对比、误区澄清
# 输出：概念解释 + 探索任务
def create_rag_agent(system_prompt: str = DEFAULT_RAG_SYSTEM_PROMPT):
    """
    创建带有 RAG 检索工具的 Agent。
    """
    return create_agent(
        model=ollama_qwen_llm,
        tools=[retrieve_context],
        system_prompt=system_prompt,
    )
