"""
Query 理解层：对用户 query 做零延迟正则分析，输出意图 + 实体 + 过滤条件 + 动态 RRF 权重。

v3: 新增动态 RRF 权重 profile、同义词扩展、实体标准化。
"""

import re
from dataclasses import dataclass, field

from app.core.config import settings

# ── 中文数字→阿拉伯数字映射 ──
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


# ── 正则模式 ──
_ARTICLE_PATTERN = re.compile(r"[《]?(.+?)[》]?\s*第?\s*(\d+)\s*条")
_ARTICLE_CN_PATTERN = re.compile(r"[《]?(.+?)[》]?\s*第([零一二三四五六七八九十百千]+)条")
_CASE_PATTERN = re.compile(r"[\(（]\d{4}[\)）].+?号")

# ── 法律名称：别名→标准名映射 ──
_LAW_ALIASES: dict[str, str] = {
    "劳动合同法": "劳动合同法",
    "劳合法": "劳动合同法",
    "劳动法": "劳动法",
    "社会保险法": "社会保险法",
    "社保法": "社会保险法",
    "就业促进法": "就业促进法",
    "工伤保险条例": "工伤保险条例",
    "工伤条例": "工伤保险条例",
    "劳动争议调解仲裁法": "劳动争议调解仲裁法",
    "仲裁法": "劳动争议调解仲裁法",
    "民法典": "民法典",
    "公司法": "公司法",
    "合同法": "合同法",
    "刑法": "刑法",
    "民事诉讼法": "民事诉讼法",
    "劳动合同法实施条例": "劳动合同法实施条例",
    "实施条例": "劳动合同法实施条例",
    "女职工劳动保护特别规定": "女职工劳动保护特别规定",
    "女职工保护": "女职工劳动保护特别规定",
    "工资支付暂行规定": "工资支付暂行规定",
    "最低工资规定": "最低工资规定",
    "职工带薪年休假条例": "职工带薪年休假条例",
    "年休假条例": "职工带薪年休假条例",
}
# 为向后兼容保留列表
_LAW_KEYWORDS = list(set(_LAW_ALIASES.values()))

# ── 同义词扩展表（口语→书面） ──
_SYNONYM_MAP: dict[str, list[str]] = {
    "加班费": ["加班工资", "延长工作时间报酬"],
    "开除": ["解除劳动合同", "辞退", "单方解除"],
    "辞退": ["解除劳动合同", "开除", "单方解除"],
    "炒鱿鱼": ["解除劳动合同", "辞退"],
    "裁员": ["经济性裁员", "裁减人员"],
    "五险一金": ["社会保险", "住房公积金"],
    "社保": ["社会保险"],
    "工伤": ["工伤认定", "工伤保险"],
    "产假": ["产假", "生育假"],
    "年假": ["年休假", "带薪年休假"],
    "试用期": ["试用期"],
    "赔偿": ["经济补偿", "赔偿金", "损害赔偿"],
    "补偿": ["经济补偿", "经济补偿金"],
    "双倍工资": ["二倍工资", "双倍工资"],
    "N+1": ["经济补偿", "代通知金"],
    "N加1": ["经济补偿", "代通知金"],
    "2N": ["违法解除劳动合同赔偿金"],
    "合同到期": ["劳动合同终止", "劳动合同期满"],
    "不续签": ["劳动合同终止", "不续订"],
    "竞业": ["竞业限制", "竞业禁止"],
    "保密": ["保密义务", "保密协议", "商业秘密"],
    "欠薪": ["拖欠工资", "克扣工资"],
    "最低工资": ["最低工资标准"],
}

# ── 动态 RRF 权重 profile ──
# 键: "rule", "bm25", "meta", "dense"
_RRF_PROFILES: dict[str, dict[str, float]] = {
    "law_article_exact": {"rule": 3.0, "bm25": 1.5, "meta": 1.0, "dense": 0.3},
    "law_article_fuzzy": {"rule": 1.5, "bm25": 1.2, "meta": 1.0, "dense": 0.8},
    "case_lookup":       {"rule": 0.5, "bm25": 1.0, "meta": 1.2, "dense": 1.5},
    "concept_explain":   {"rule": 0.3, "bm25": 0.6, "meta": 0.5, "dense": 2.0},
    "general":           {"rule": 0.5, "bm25": 0.8, "meta": 0.5, "dense": 1.0},
}


@dataclass
class QueryAnalysis:
    """Query 分析结果。"""

    intent: str = "general"  # law_article | case_lookup | concept_explain | general
    entities: dict = field(default_factory=dict)
    metadata_filters: dict = field(default_factory=dict)
    bm25_boost: float = 0.0  # 向后兼容
    rrf_weights: dict = field(default_factory=lambda: _RRF_PROFILES["general"].copy())
    hyde_enabled: bool = False
    expanded_query: str = ""  # 同义词扩展后的 query（用于 dense 检索）


def _normalize_law_name(text: str) -> str | None:
    """在 query 中查找法律名称，返回标准名。"""
    # 按长度降序匹配，避免 "劳动合同法实施条例" 被 "劳动合同法" 先匹配
    for alias in sorted(_LAW_ALIASES, key=len, reverse=True):
        if alias in text:
            return _LAW_ALIASES[alias]
    return None


def _expand_synonyms(query: str) -> str:
    """对 query 做同义词扩展，返回扩展后的查询。"""
    expansions: list[str] = []
    for term, synonyms in _SYNONYM_MAP.items():
        if term in query:
            expansions.extend(synonyms)

    if not expansions:
        return query

    # 去重并拼接
    unique = list(dict.fromkeys(expansions))
    return query + " " + " ".join(unique)


def analyze_query(query: str) -> QueryAnalysis:
    """
    对 query 做正则分析，提取意图、实体、过滤条件和动态 RRF 权重。

    优先级链：law_article → case_lookup → concept_explain → general
    """
    analysis = QueryAnalysis()
    entities: dict = {}

    # ── 1. 法律名+条号 ──
    article_match = _ARTICLE_PATTERN.search(query)
    cn_match = _ARTICLE_CN_PATTERN.search(query)
    if article_match or cn_match:
        if article_match:
            law_name = article_match.group(1).strip()
            article_no = article_match.group(2).strip()
        else:
            law_name = cn_match.group(1).strip()
            article_no = str(_cn_to_int(cn_match.group(2)))

        # 标准化法律名
        canonical = _normalize_law_name(law_name)
        if canonical:
            law_name = canonical

        entities["law_name"] = law_name
        entities["article_no"] = article_no
        analysis.intent = "law_article"
        analysis.bm25_boost = 0.3
        analysis.rrf_weights = _RRF_PROFILES["law_article_exact"].copy()

        for known_law in _LAW_KEYWORDS:
            if known_law in law_name or law_name in known_law:
                analysis.metadata_filters["doc_type"] = "statute"
                break

    # ── 2. 案号 ──
    case_match = _CASE_PATTERN.search(query)
    if case_match:
        entities["case_id"] = case_match.group(0)
        if analysis.intent == "general":
            analysis.intent = "case_lookup"
            analysis.bm25_boost = 0.2
            analysis.rrf_weights = _RRF_PROFILES["case_lookup"].copy()
            analysis.hyde_enabled = True

    # ── 2b. 案例自然语言关键词 ──
    if analysis.intent == "general":
        strong_case_kw = ["案件", "案例", "纠纷案", "争议案", "赔偿案", "认定案", "怎么判", "如何判"]
        weak_case_kw = [
            "案", "判", "裁判", "判决", "裁定", "仲裁", "法院",
            "认定", "败诉", "胜诉", "起诉", "上诉", "举证",
        ]
        if any(kw in query for kw in strong_case_kw):
            analysis.intent = "case_lookup"
            analysis.bm25_boost = 0.2
            analysis.rrf_weights = _RRF_PROFILES["case_lookup"].copy()
            analysis.hyde_enabled = True
        elif sum(1 for kw in weak_case_kw if kw in query) >= 2:
            analysis.intent = "case_lookup"
            analysis.bm25_boost = 0.2
            analysis.rrf_weights = _RRF_PROFILES["case_lookup"].copy()
            analysis.hyde_enabled = True

    # ── 3. 概念/定义类 ──
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
    ends_with_question = query.rstrip("？?").endswith("吗")
    if not is_action_query and (any(kw in query for kw in concept_keywords) or ends_with_question) and analysis.intent == "general":
        analysis.intent = "concept_explain"
        analysis.bm25_boost = 0.1
        analysis.rrf_weights = _RRF_PROFILES["concept_explain"].copy()
        analysis.hyde_enabled = True

    # ── 4. 检查已知法律名称（无条号） ──
    if "law_name" not in entities:
        canonical = _normalize_law_name(query)
        if canonical:
            entities["law_name"] = canonical
            if analysis.intent == "general":
                analysis.bm25_boost = 0.15
            if analysis.intent == "law_article":
                # 有法律名但无条号 → 模糊法条查询
                analysis.rrf_weights = _RRF_PROFILES["law_article_fuzzy"].copy()

    # ── 5. 同义词扩展 ──
    analysis.expanded_query = _expand_synonyms(query)

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
