"""
检索验证器：评估检索结果与 query 的相关性。

不相关时触发 query 重写 + 重试机制。
"""

import time
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.logging import get_traced_logger
from app.llm.model_factory import chat_llm


class RelevanceGrade(BaseModel):
    """检索结果相关性评分。"""
    is_relevant: bool = Field(description="检索结果是否与用户问题相关")
    reason: str = Field(description="判断理由（一句话）")


class QueryRewrite(BaseModel):
    """查询重写结果。"""
    rewritten_query: str = Field(description="重写后的查询")
    strategy: str = Field(description="重写策略说明")


async def validate_retrieval(
    query: str,
    docs: List[Document],
    threshold: int = 1,
) -> bool:
    """
    验证检索结果是否与 query 相关。

    检查 top-3 文档，至少 threshold 个相关才算通过。

    Args:
        query: 用户查询
        docs: 检索到的文档列表
        threshold: 至少需要多少个相关文档

    Returns:
        True 表示检索结果可用，False 表示需要重试
    """
    logger = get_traced_logger(__name__)

    if not docs:
        return False

    t0 = time.perf_counter()
    logger.info(
        "retrieval_validation_started",
        query_preview=query[:50],
        doc_count=len(docs),
        threshold=threshold,
    )

    top_docs = docs[:3]
    relevant_count = 0

    llm = chat_llm.with_structured_output(RelevanceGrade, method="json_schema")

    for doc in top_docs:
        try:
            grade = await llm.ainvoke([
                SystemMessage(content=(
                    "你是检索质量评审员。判断以下文档片段是否与用户问题相关。\n"
                    "相关的标准：文档内容能部分或全部回答用户问题，或提供有用的背景信息。\n"
                    "不相关的标准：文档内容与问题完全无关，或仅有表面关键词重叠但语义不同。"
                )),
                HumanMessage(content=(
                    f"用户问题：{query}\n\n"
                    f"文档片段：{doc.page_content[:800]}\n\n"
                    "请判断这个文档片段是否与用户问题相关。"
                )),
            ])
            parsed = grade if isinstance(grade, RelevanceGrade) else RelevanceGrade.model_validate(grade)
            if parsed.is_relevant:
                relevant_count += 1
        except Exception as exc:
            logger.warning("relevance_grading_failed_default_relevant", error=str(exc))
            relevant_count += 1  # 失败时默认相关，避免误判

    is_valid = relevant_count >= threshold
    logger.info(
        "retrieval_validation_completed",
        query_preview=query[:50],
        relevant_count=relevant_count,
        total_checked=len(top_docs),
        passed=is_valid,
        elapsed_s=round(time.perf_counter() - t0, 3),
    )
    return is_valid


async def rewrite_query(query: str) -> str:
    """
    重写用户查询以提升检索效果。

    策略：扩展关键词、补充同义词、明确检索意图。
    """
    logger = get_traced_logger(__name__)
    t0 = time.perf_counter()
    llm = chat_llm.with_structured_output(QueryRewrite, method="json_schema")
    try:
        result = await llm.ainvoke([
            SystemMessage(content=(
                "你是查询优化专家。用户的原始查询检索效果不佳，请重写查询以提升检索召回率。\n"
                "重写策略：\n"
                "1. 补充同义词和相关术语\n"
                "2. 如果是口语化表达，转换为法律/教育领域的正式术语\n"
                "3. 如果问题模糊，尝试明确化\n"
                "4. 保持原始查询的核心意图不变\n"
                "输出重写后的查询（一句话，不超过100字）。"
            )),
            HumanMessage(content=f"原始查询：{query}\n\n请重写："),
        ])
        parsed = result if isinstance(result, QueryRewrite) else QueryRewrite.model_validate(result)
        logger.info(
            "query_rewrite_completed",
            original_preview=query[:50],
            rewritten_preview=parsed.rewritten_query[:50],
            strategy=parsed.strategy,
            elapsed_s=round(time.perf_counter() - t0, 3),
        )
        return parsed.rewritten_query
    except Exception as exc:
        logger.warning("query_rewrite_failed_using_original", error=str(exc))
        return query


async def retrieve_with_validation(
    query: str,
    retriever,
    analysis,
    k: int = 6,
    max_retries: int = 1,
) -> List[Document]:
    """
    带检索验证的完整检索流程（供外部调用的包装函数）。

    执行流程：
    1. 用原始 query 检索
    2. 验证相关性；若通过则直接返回
    3. 不通过则重写 query，用新 query 重新分析并检索（最多 max_retries 次）

    Args:
        query: 用户原始查询
        retriever: HybridRetriever 实例
        analysis: 原始 QueryAnalysis
        k: 期望返回文档数
        max_retries: 最多重试次数

    Returns:
        检索文档列表
    """
    from app.retrieval.query_analyzer import analyze_query

    logger = get_traced_logger(__name__)
    original_query = query
    current_query = query
    current_analysis = analysis

    for attempt in range(max_retries + 1):
        docs = retriever.retrieve(current_query, current_analysis, k=k)
        if await validate_retrieval(current_query, docs):
            return docs
        if attempt < max_retries:
            logger.info(
                "retrieval_validation_retry",
                attempt=attempt + 1,
            )
            current_query = await rewrite_query(original_query)
            current_analysis = analyze_query(current_query)

    # 所有重试均未通过，返回最后一次检索结果（降级处理）
    logger.warning(
        "retrieval_validation_all_retries_exhausted",
        query_preview=original_query[:50],
    )
    return docs
