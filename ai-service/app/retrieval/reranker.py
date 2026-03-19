"""
Reranker：对多路召回结果做重排序。

主方案：FlashRank cross-encoder（轻量、快速、多语言支持）。
降级方案：jieba 关键词 + 文本相似度（FlashRank 不可用时自动降级）。
"""

import logging
from typing import List, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# 懒加载 FlashRank
_ranker = None
_flashrank_available = None


def _get_flashrank_ranker():
    """懒加载 FlashRank Ranker 单例。"""
    global _ranker, _flashrank_available
    if _flashrank_available is None:
        try:
            from flashrank import Ranker, RerankRequest
            _ranker = Ranker(model_name="ms-marco-MultiBERT-L-12", cache_dir="/tmp/flashrank_cache")
            _flashrank_available = True
            logger.info("FlashRank Reranker 加载成功: ms-marco-MultiBERT-L-12")
        except Exception as exc:
            _flashrank_available = False
            logger.warning("FlashRank 不可用，将使用降级方案: %s", str(exc))
    return _ranker if _flashrank_available else None


def rerank(
    query: str,
    docs: List[Document],
    top_k: int = 6,
) -> List[Tuple[Document, float]]:
    """
    对文档列表重排序。优先使用 FlashRank，不可用时降级到关键词匹配。

    Args:
        query: 用户查询
        docs: 待排序文档列表
        top_k: 返回前 top_k 个结果

    Returns:
        (Document, score) 列表，按 score 降序
    """
    if not docs:
        return []

    ranker = _get_flashrank_ranker()
    if ranker is not None:
        return _rerank_with_flashrank(ranker, query, docs, top_k)
    return _rerank_fallback(query, docs, top_k)


def _rerank_with_flashrank(
    ranker,
    query: str,
    docs: List[Document],
    top_k: int,
) -> List[Tuple[Document, float]]:
    """使用 FlashRank cross-encoder 重排序。"""
    from flashrank import RerankRequest

    passages = [
        {"id": str(i), "text": doc.page_content[:2000]}
        for i, doc in enumerate(docs)
    ]

    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)

    scored: List[Tuple[Document, float]] = []
    for result in results[:top_k]:
        idx = int(result["id"])
        score = float(result["score"])
        scored.append((docs[idx], score))

    return scored


def _rerank_fallback(
    query: str,
    docs: List[Document],
    top_k: int,
) -> List[Tuple[Document, float]]:
    """降级方案：jieba 分词 + 关键词命中率排序。"""
    import jieba

    query_tokens = set(jieba.cut(query))
    scored: List[Tuple[Document, float]] = []

    for doc in docs:
        content = doc.page_content or ""
        content_tokens = set(jieba.cut(content[:1000]))

        # 关键词重叠率
        if query_tokens:
            overlap = len(query_tokens & content_tokens) / len(query_tokens)
        else:
            overlap = 0.0

        # BM25 分数加成（如果有）
        bm25_bonus = min(float(doc.metadata.get("_bm25_score", 0)) / 20, 0.3)

        score = min(overlap + bm25_bonus, 1.0)
        scored.append((doc, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
