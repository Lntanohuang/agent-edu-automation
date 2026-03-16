"""
hybrid_retriever unit tests. Uses unittest.mock patch, no external services required.
"""
import os
import sys
from unittest.mock import MagicMock, patch

AI_SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AI_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, AI_SERVICE_ROOT)

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost/v1")
os.environ.setdefault("MONGODB_ENABLED", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

import pytest
from langchain_core.documents import Document
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.query_analyzer import analyze_query


def _make_doc(content: str, metadata: dict = None) -> Document:
    return Document(page_content=content, metadata=metadata or {})


def _make_mock_vector_store(docs=None):
    vs = MagicMock()
    vs.similarity_search.return_value = docs or []
    try:
        collection = MagicMock()
        collection.get.return_value = {"documents": [], "metadatas": [], "ids": []}
        vs._collection = collection
    except Exception:
        pass
    vs.get.return_value = {"documents": [], "metadatas": [], "ids": []}
    return vs


class TestHybridRetrieverInvalidate:
    def test_invalidate_resets_bm25(self):
        with patch("app.retrieval.hybrid_retriever.get_rag_vector_store",
                   return_value=_make_mock_vector_store()):
            hr = HybridRetriever()
            # Manually set a fake bm25
            hr._bm25 = MagicMock()
            hr.invalidate()
            assert hr._bm25 is None
            assert hr._bm25_docs == []
            assert hr._bm25_corpus == []
            assert hr._index_hash is None


class TestHybridRetrieverDedup:
    def test_retrieve_deduplicates_docs(self):
        """Documents with identical content should be deduplicated to one entry."""
        dup_content = "这是重复文档内容"
        doc1 = _make_doc(dup_content)
        doc2 = _make_doc(dup_content)  # same content
        doc3 = _make_doc("不同内容")

        mock_vs = _make_mock_vector_store([doc1, doc2, doc3])

        with patch("app.retrieval.hybrid_retriever.get_rag_vector_store", return_value=mock_vs), \
             patch("app.retrieval.hybrid_retriever.rerank",
                   side_effect=lambda q, docs, top_k: [(d, 1.0) for d in docs[:top_k]]), \
             patch("app.retrieval.hybrid_retriever.log_retrieval_metrics"):
            hr = HybridRetriever()
            # Inject empty BM25 corpus to avoid real ChromaDB
            hr._bm25 = None
            hr._bm25_docs = []
            hr._bm25_corpus = []

            analysis = analyze_query("测试查询")
            results = hr.retrieve("测试查询", analysis, k=6)

            # Duplicate content must appear at most once
            contents = [d.page_content for d in results]
            assert contents.count(dup_content) <= 1


class TestRuleRecall:
    def test_rule_recall_hits_with_law_and_article(self):
        """Rule recall should return results when both law_name and article_no are present."""
        doc = _make_doc(
            "第47条 经济补偿按工作年限计算",
            {"law_name": "劳动合同法", "article_no": "47"}
        )

        with patch("app.retrieval.hybrid_retriever.get_rag_vector_store",
                   return_value=_make_mock_vector_store()):
            hr = HybridRetriever()
            hr._bm25_docs = [doc]
            hr._bm25 = MagicMock()  # Mark as initialised

            analysis = analyze_query("劳动合同法第47条")
            results = hr._rule_recall(analysis)
            assert len(results) > 0

    def test_rule_recall_empty_when_no_article(self):
        """With only law_name and no article_no, and empty corpus, should return empty list."""
        with patch("app.retrieval.hybrid_retriever.get_rag_vector_store",
                   return_value=_make_mock_vector_store()):
            hr = HybridRetriever()
            hr._bm25_docs = []  # Empty corpus
            hr._bm25 = MagicMock()

            analysis = analyze_query("劳动合同法有什么规定")
            # No article number, empty corpus -> no exact match
            results = hr._rule_recall(analysis)
            assert results == []


class TestEmptyCorpus:
    def test_retrieve_with_empty_corpus_does_not_crash(self):
        """Should not crash when ChromaDB has no documents."""
        mock_vs = _make_mock_vector_store([])

        with patch("app.retrieval.hybrid_retriever.get_rag_vector_store", return_value=mock_vs), \
             patch("app.retrieval.hybrid_retriever.rerank",
                   side_effect=lambda q, docs, top_k: []), \
             patch("app.retrieval.hybrid_retriever.log_retrieval_metrics"):
            hr = HybridRetriever()
            analysis = analyze_query("测试")
            results = hr.retrieve("测试", analysis, k=6)
            assert isinstance(results, list)
