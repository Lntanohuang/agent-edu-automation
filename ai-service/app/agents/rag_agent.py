from langchain.agents import create_agent

from app.llm.model_factory import ollama_qwen_llm
from app.prompts.rag_prompts import DEFAULT_RAG_SYSTEM_PROMPT
from app.tools.rag_tool import retrieve_context




def create_rag_agent(system_prompt: str = DEFAULT_RAG_SYSTEM_PROMPT):
    """
    创建带有 RAG 检索工具的 Agent。
    """
    return create_agent(
        model=ollama_qwen_llm,
        tools=[retrieve_context],
        system_prompt=system_prompt,
    )
