"""
Query 理解层：对用户 query 做零延迟正则分析，输出意图 + 实体 + 过滤条件。
"""

import re
from dataclasses import dataclass, field

from app.core.config import settings

# 中文数字→阿拉伯数字映射
_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
              "百": 100, "千": 1000}


def _cn_to_int(cn: str) -> int:
    """简易中文数字转整数：支持 '四十七'、'三百八十七' 等。"""
    if not cn:
        return 0
    result = 0
    cur = 0
    for ch in cn:
        v = _CN_DIGITS.get(ch)
        if v is None:
            continue
        if v >= 10:  # 十/百/千
            result += max(cur, 1) * v
            cur = 0
        else:
            cur = cur * 10 + v if cur else v
    return result + cur


# 正则模式：法律名 + 条号（支持阿拉伯数字和中文数字）
_ARTICLE_PATTERN = re.compile(r"[《]?(.+?)[》]?\s*第?\s*(\d+)\s*条")
_ARTICLE_CN_PATTERN = re.compile(r"[《]?(.+?)[》]?\s*第([零一二三四五六七八九十百千]+)条")
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

    # 1. 尝试匹配法律名+条号（阿拉伯数字优先，再试中文数字）
    article_match = _ARTICLE_PATTERN.search(query)
    cn_match = _ARTICLE_CN_PATTERN.search(query)
    if article_match or cn_match:
        if article_match:
            law_name = article_match.group(1).strip()
            article_no = article_match.group(2).strip()
        else:
            law_name = cn_match.group(1).strip()
            article_no = str(_cn_to_int(cn_match.group(2)))
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

    # 2b. 案例类自然语言关键词（没有正式案号但在讨论案例）
    if analysis.intent == "general":
        # 强案例关键词（单个即触发）
        strong_case_kw = ["案件", "案例", "纠纷案", "争议案", "赔偿案", "认定案", "怎么判", "如何判"]
        # 弱案例关键词（需 >= 2 个）
        weak_case_kw = [
            "案", "判", "裁判", "判决", "裁定", "仲裁", "法院",
            "认定", "败诉", "胜诉", "起诉", "上诉", "举证",
        ]
        if any(kw in query for kw in strong_case_kw):
            analysis.intent = "case_lookup"
            analysis.bm25_boost = 0.2
        elif sum(1 for kw in weak_case_kw if kw in query) >= 2:
            analysis.intent = "case_lookup"
            analysis.bm25_boost = 0.2

    # 3. 概念/定义类查询
    # 先检查是否为「行动/求助」型 — 这类应保持 general
    action_keywords = [
        "怎么办", "怎么维权", "咋办", "该怎么做", "怎么做",
        "怎么赔偿", "怎么处理",
    ]
    is_action_query = any(kw in query for kw in action_keywords)

    concept_keywords = [
        "什么意思", "概念", "定义", "含义", "是什么", "怎么理解",
        "什么是", "什么叫", "哪些", "哪几种", "几种",
        "包含", "包括", "区别", "不同", "区分",
        "最长", "最多", "最少", "多久", "几天", "几年", "几倍",
        "什么情况", "什么条件", "能不能", "能否", "是否",
        "算不算", "合法吗", "违法吗",
        "怎么补偿", "怎么计算", "如何计算", "如何补偿",
        "需要什么", "有什么",
    ]
    # "...吗" 结尾但非行动型的疑问句 → 概念类
    ends_with_question = query.rstrip("？?").endswith("吗")
    if not is_action_query and (any(kw in query for kw in concept_keywords) or ends_with_question) and analysis.intent == "general":
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
