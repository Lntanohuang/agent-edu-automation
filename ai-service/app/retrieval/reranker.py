"""
Reranker：对多路召回结果做重排序。

当前实现：基于 difflib.SequenceMatcher 的轻量文本相似度排序。
预留：Ollama cross-encoder rerank 接口。
"""

import difflib
from typing import List, Tuple

from langchain_core.documents import Document

from app.core.logging import get_logger

logger = get_logger(__name__)


def rerank(
    query: str,
    docs: List[Document],
    top_k: int = 6,
) -> List[Tuple[Document, float]]:
    """
    对文档列表按与 query 的文本相似度重排序。

    Args:
        query: 用户查询
        docs: 待排序文档列表
        top_k: 返回前 top_k 个结果

    Returns:
        (Document, score) 列表，按 score 降序
    """
    if not docs:
        return []

    scored: List[Tuple[Document, float]] = []
    query_lower = query.lower()

    for doc in docs:
        content = doc.page_content or ""
        # 基础文本相似度
        ratio = difflib.SequenceMatcher(None, query_lower, content[:500].lower()).ratio()

        # 关键词命中加分：query 中每个词在 doc 中出现则加分
        query_tokens = set(query_lower)
        content_lower = content.lower()
        keyword_bonus = sum(0.05 for token in query_tokens if token in content_lower)
        keyword_bonus = min(keyword_bonus, 0.3)  # 上限

        score = min(ratio + keyword_bonus, 1.0)
        scored.append((doc, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


async def rerank_with_ollama(
    query: str,
    docs: List[Document],
    top_k: int = 6,
    model: str = "bge-reranker-v2-m3",
) -> List[Tuple[Document, float]]:
    """
    预留接口：使用 Ollama 支持的 cross-encoder 模型做重排序。

    当 Ollama 支持 rerank API 时实现此函数。
    目前 fallback 到 SequenceMatcher 排序。
    """
    logger.info("Ollama rerank 暂未实现，使用 SequenceMatcher fallback", model=model)
    return rerank(query, docs, top_k)
