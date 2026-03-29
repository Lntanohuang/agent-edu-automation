"""
Reranker：对多路召回结果做重排序。

主方案：FlashRank cross-encoder + 滑动窗口分段打分。
多样性：MMR (Maximal Marginal Relevance) 避免返回高度重复内容。
降级方案：jieba 关键词 + 文本相似度（FlashRank 不可用时自动降级）。
"""

import logging
from typing import List, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# 懒加载 FlashRank
_ranker = None
_flashrank_available = None

# 滑动窗口参数
_WINDOW_SIZE = 512
_WINDOW_OVERLAP = 128


def _get_flashrank_ranker():
    """懒加载 FlashRank Ranker 单例。"""
    global _ranker, _flashrank_available
    if _flashrank_available is None:
        try:
            from flashrank import Ranker
            _ranker = Ranker(model_name="ms-marco-MultiBERT-L-12", cache_dir="/tmp/flashrank_cache")
            _flashrank_available = True
            logger.info("FlashRank Reranker 加载成功: ms-marco-MultiBERT-L-12")
        except Exception as exc:
            _flashrank_available = False
            logger.warning("FlashRank 不可用，将使用降级方案: %s", str(exc))
    return _ranker if _flashrank_available else None


def _sliding_window_score(ranker, query: str, content: str) -> float:
    """对长文档做滑动窗口 rerank，取最高分窗口代表该文档。"""
    from flashrank import RerankRequest

    if len(content) <= _WINDOW_SIZE:
        result = ranker.rerank(RerankRequest(query=query, passages=[{"text": content}]))
        return float(result[0]["score"]) if result else 0.0

    windows: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + _WINDOW_SIZE, len(content))
        windows.append(content[start:end])
        if end >= len(content):
            break
        start += _WINDOW_SIZE - _WINDOW_OVERLAP

    passages = [{"text": w} for w in windows]
    results = ranker.rerank(RerankRequest(query=query, passages=passages))
    if not results:
        return 0.0
    return max(float(r["score"]) for r in results)


def mmr_rerank(
    docs_with_scores: List[Tuple[Document, float]],
    lambda_param: float = 0.7,
    top_k: int = 6,
) -> List[Tuple[Document, float]]:
    """MMR (Maximal Marginal Relevance) 多样性重排。

    score_final = lambda * relevance - (1-lambda) * max_similarity(d, selected)
    使用 jieba 词袋 Jaccard 相似度（避免额外 embedding 调用）。
    """
    if len(docs_with_scores) <= 1:
        return docs_with_scores[:top_k]

    import jieba

    def _tokenize(text: str) -> set:
        return set(jieba.cut(text[:1000]))

    token_sets = [_tokenize(doc.page_content or "") for doc, _ in docs_with_scores]

    selected: list[int] = []
    remaining = list(range(len(docs_with_scores)))

    # 第一个选最高分的
    best_idx = max(remaining, key=lambda i: docs_with_scores[i][1])
    selected.append(best_idx)
    remaining.remove(best_idx)

    while len(selected) < top_k and remaining:
        best_mmr_score = -float("inf")
        best_candidate = remaining[0]

        for i in remaining:
            relevance = docs_with_scores[i][1]
            max_sim = 0.0
            for j in selected:
                intersection = len(token_sets[i] & token_sets[j])
                union = len(token_sets[i] | token_sets[j])
                sim = intersection / union if union > 0 else 0.0
                max_sim = max(max_sim, sim)

            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_candidate = i

        selected.append(best_candidate)
        remaining.remove(best_candidate)

    return [docs_with_scores[i] for i in selected]


def rerank(
    query: str,
    docs: List[Document],
    top_k: int = 6,
    use_mmr: bool = True,
    mmr_lambda: float = 0.7,
) -> List[Tuple[Document, float]]:
    """对文档列表重排序，可选 MMR 多样性重排。

    Args:
        query: 用户查询
        docs: 待排序文档列表
        top_k: 返回前 top_k 个结果
        use_mmr: 是否启用 MMR 多样性重排
        mmr_lambda: MMR 参数，越大越偏重相关性
    """
    if not docs:
        return []

    ranker = _get_flashrank_ranker()
    if ranker is not None:
        scored = _rerank_with_flashrank(ranker, query, docs)
    else:
        scored = _rerank_fallback(query, docs)

    # MMR 多样性重排
    if use_mmr and len(scored) > top_k:
        return mmr_rerank(scored, lambda_param=mmr_lambda, top_k=top_k)
    return scored[:top_k]


def _rerank_with_flashrank(
    ranker,
    query: str,
    docs: List[Document],
) -> List[Tuple[Document, float]]:
    """使用 FlashRank cross-encoder + 滑动窗口重排序。"""
    scored: List[Tuple[Document, float]] = []
    for doc in docs:
        content = doc.page_content or ""
        if not content:
            scored.append((doc, 0.0))
            continue
        score = _sliding_window_score(ranker, query, content)
        scored.append((doc, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _rerank_fallback(
    query: str,
    docs: List[Document],
) -> List[Tuple[Document, float]]:
    """降级方案：jieba 分词 + 关键词命中率排序。"""
    import jieba

    query_tokens = set(jieba.cut(query))
    scored: List[Tuple[Document, float]] = []

    for doc in docs:
        content = doc.page_content or ""
        content_tokens = set(jieba.cut(content[:1000]))

        if query_tokens:
            overlap = len(query_tokens & content_tokens) / len(query_tokens)
        else:
            overlap = 0.0

        bm25_bonus = min(float(doc.metadata.get("_bm25_score", 0)) / 20, 0.3)
        score = min(overlap + bm25_bonus, 1.0)
        scored.append((doc, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# 向后兼容别名
do_rerank = rerank
