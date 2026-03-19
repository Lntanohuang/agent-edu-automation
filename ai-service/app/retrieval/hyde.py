"""
HyDE (Hypothetical Document Embeddings) 查询增强。

核心思路：让 LLM 先生成一段假设性回答，用这段回答做向量检索，
因为假设性回答的用词更接近知识库中的文档，检索召回率更高。

仅对 concept_explain 和 general 意图启用（law_article 和 case_lookup 靠精确匹配更好）。
"""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.model_factory import chat_llm

logger = logging.getLogger(__name__)

_HYDE_SYSTEM_PROMPT = """你是一个法学教育领域的知识库文档片段生成器。
给定一个用户问题，请直接写出一段可能出现在教材或法律条文中的回答文本（200-400字）。
要求：
1. 使用教材/法规的正式语言风格
2. 包含可能的关键术语、条文号、法律名称
3. 不要加引言或总结，直接给出内容片段
4. 如果涉及具体法条，写出"第X条"这样的表述"""


async def generate_hypothetical_document(query: str) -> Optional[str]:
    """
    用 LLM 生成假设性文档片段，用于增强向量检索。

    Args:
        query: 用户原始查询

    Returns:
        假设性文档文本，失败时返回 None
    """
    try:
        response = await chat_llm.ainvoke([
            SystemMessage(content=_HYDE_SYSTEM_PROMPT),
            HumanMessage(content=f"用户问题：{query}\n\n请生成一段可能出现在知识库中的文档片段："),
        ])
        hypothesis = response.content.strip()
        if hypothesis and len(hypothesis) > 50:
            logger.info("HyDE 生成成功 query=%s hypothesis_len=%d", query[:50], len(hypothesis))
            return hypothesis
        logger.warning("HyDE 生成内容过短，跳过 length=%d", len(hypothesis))
        return None
    except Exception as exc:
        logger.warning("HyDE 生成失败，跳过 error=%s", str(exc))
        return None


def generate_hypothetical_document_sync(query: str) -> Optional[str]:
    """
    同步版本的 HyDE 生成，供 retrieve()（同步方法）直接调用。

    Args:
        query: 用户原始查询

    Returns:
        假设性文档文本，失败时返回 None
    """
    try:
        response = chat_llm.invoke([
            SystemMessage(content=_HYDE_SYSTEM_PROMPT),
            HumanMessage(content=f"用户问题：{query}\n\n请生成一段可能出现在知识库中的文档片段："),
        ])
        hypothesis = response.content.strip()
        if hypothesis and len(hypothesis) > 50:
            logger.info("HyDE 生成成功 query=%s hypothesis_len=%d", query[:50], len(hypothesis))
            return hypothesis
        logger.warning("HyDE 生成内容过短，跳过 length=%d", len(hypothesis))
        return None
    except Exception as exc:
        logger.warning("HyDE 生成失败，跳过 error=%s", str(exc))
        return None
