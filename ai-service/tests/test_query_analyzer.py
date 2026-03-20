"""
query_analyzer unit tests. No external dependencies.
"""
import os
import sys

AI_SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AI_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, AI_SERVICE_ROOT)

# Set required environment variables to prevent Settings initialisation failure
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost/v1")
os.environ.setdefault("MONGODB_ENABLED", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

import pytest
from app.retrieval.query_analyzer import analyze_query, get_k_for_intent


class TestAnalyzeQueryIntent:
    def test_law_article_with_name_and_number(self):
        result = analyze_query("劳动合同法第47条规定了什么")
        assert result.intent == "law_article"
        assert result.entities.get("law_name") is not None
        assert result.entities.get("article_no") == "47"

    def test_law_article_number_only(self):
        result = analyze_query("第39条什么内容")
        assert result.intent == "law_article"
        assert result.entities.get("article_no") == "39"

    def test_case_lookup(self):
        result = analyze_query("(2024)京01民终123号案件")
        assert result.intent == "case_lookup"
        assert "case_id" in result.entities

    def test_concept_explain(self):
        result = analyze_query("经济补偿金是什么意思")
        assert result.intent == "concept_explain"

    def test_general_intent(self):
        result = analyze_query("劳动者有哪些权益")
        assert result.intent == "general"

    def test_empty_query(self):
        result = analyze_query("")
        assert result.intent == "general"


class TestAnalyzeQueryBm25Boost:
    def test_law_article_boost(self):
        result = analyze_query("劳动合同法第47条")
        assert result.bm25_boost == pytest.approx(0.3)

    def test_case_lookup_boost(self):
        result = analyze_query("(2024)京01民终123号")
        assert result.bm25_boost == pytest.approx(0.2)

    def test_concept_boost(self):
        result = analyze_query("经济补偿金的定义是什么")
        assert result.bm25_boost == pytest.approx(0.1)

    def test_general_boost_is_zero_or_low(self):
        result = analyze_query("天气好")
        assert result.bm25_boost < 0.2

    def test_law_name_only_boost(self):
        # Only known law name, no article number -> bm25_boost=0.15
        result = analyze_query("劳动合同法有哪些规定")
        assert result.bm25_boost >= 0.1


class TestGetKForIntent:
    def test_law_article_k(self):
        k = get_k_for_intent("law_article")
        assert isinstance(k, int)
        assert k > 0

    def test_case_lookup_k(self):
        k = get_k_for_intent("case_lookup")
        assert k > 0

    def test_concept_explain_k(self):
        k = get_k_for_intent("concept_explain")
        assert k > 0

    def test_general_k(self):
        k = get_k_for_intent("general")
        assert k > 0

    def test_unknown_intent_returns_default(self):
        k = get_k_for_intent("unknown_intent")
        assert k > 0


class TestEntityExtraction:
    def test_law_name_extraction(self):
        result = analyze_query("《劳动合同法》第47条")
        assert "劳动合同法" in result.entities.get("law_name", "")

    def test_article_number_extraction(self):
        result = analyze_query("第100条规定")
        assert result.entities.get("article_no") == "100"

    def test_case_id_extraction(self):
        result = analyze_query("(2023)沪01民终456号")
        case_id = result.entities.get("case_id", "")
        assert "2023" in case_id
