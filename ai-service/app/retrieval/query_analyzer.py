"""
Query 理解层：对用户 query 做零延迟正则分析，输出意图 + 实体 + 过滤条件。
"""

import re
from dataclasses import dataclass, field

from app.core.config import settings

# 正则模式：法律名 + 条号
_ARTICLE_PATTERN = re.compile(r"[《]?(.+?)[》]?\s*第?\s*(\d+)\s*条")
# 案号模式：(2024)京01民终123号
_CASE_PATTERN = re.compile(r"[\(（]\d{4}[\)）].+?号")
# 常见法律名称关键词
_LAW_KEYWORDS = [
    "劳动合同法", "劳动法", "社会保险法", "就业促进法",
    "工伤保险条例", "劳动争议调解仲裁法", "民法典",
    "公司法", "合同法", "刑法", "民事诉讼法",
]


@dataclass
class QueryAnalysis:
    """Query 分析结果。"""

    intent: str = "general"  # law_article | case_lookup | concept_explain | general
    entities: dict = field(default_factory=dict)  # {"law_name": ..., "article_no": ..., "case_id": ...}
    metadata_filters: dict = field(default_factory=dict)  # {"book_label": ..., "doc_type": ...}
    bm25_boost: float = 0.0  # 0.0~0.3，规则召回匹配到时调高 BM25 权重


def analyze_query(query: str) -> QueryAnalysis:
    """
    对 query 做正则分析，提取意图、实体和过滤条件。

    - 匹配到法律名+条号 → intent=law_article, bm25_boost=0.3
    - 匹配到案号 → intent=case_lookup, bm25_boost=0.2
    - 包含"什么意思"/"概念"/"定义" → intent=concept_explain
    - 其他 → intent=general
    """
    analysis = QueryAnalysis()
    entities: dict = {}

    # 1. 尝试匹配法律名+条号
    article_match = _ARTICLE_PATTERN.search(query)
    if article_match:
        law_name = article_match.group(1).strip()
        article_no = article_match.group(2).strip()
        entities["law_name"] = law_name
        entities["article_no"] = article_no
        analysis.intent = "law_article"
        analysis.bm25_boost = 0.3
        # 如果法律名在已知列表中，可做 metadata filter
        for known_law in _LAW_KEYWORDS:
            if known_law in law_name or law_name in known_law:
                analysis.metadata_filters["doc_type"] = "statute"
                break

    # 2. 尝试匹配案号
    case_match = _CASE_PATTERN.search(query)
    if case_match:
        entities["case_id"] = case_match.group(0)
        if analysis.intent == "general":
            analysis.intent = "case_lookup"
            analysis.bm25_boost = 0.2

    # 3. 概念/定义类查询
    concept_keywords = ["什么意思", "概念", "定义", "含义", "是什么", "怎么理解"]
    if any(kw in query for kw in concept_keywords) and analysis.intent == "general":
        analysis.intent = "concept_explain"
        analysis.bm25_boost = 0.1

    # 4. 检查是否提到已知法律名称（即使没有条号）
    if "law_name" not in entities:
        for law in _LAW_KEYWORDS:
            if law in query:
                entities["law_name"] = law
                if analysis.intent == "general":
                    analysis.bm25_boost = 0.15
                break

    analysis.entities = entities
    return analysis


def get_k_for_intent(intent: str) -> int:
    """根据意图返回默认检索 k 值。"""
    k_map = {
        "law_article": getattr(settings, "retrieval_k_law_article", 4),
        "case_lookup": getattr(settings, "retrieval_k_case_lookup", 8),
        "concept_explain": getattr(settings, "retrieval_k_concept", 6),
        "general": getattr(settings, "retrieval_k_default", 6),
    }
    return k_map.get(intent, 6)
