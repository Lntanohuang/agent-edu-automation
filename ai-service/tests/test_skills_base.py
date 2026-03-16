"""
Tests for app.skills.base utility functions.
Pure functions — no mocking needed.
"""
import pytest
from langchain_core.documents import Document

from app.skills.base import (
    build_context_text,
    build_sources,
    collect_book_labels,
    resolve_book_label,
)


# ── resolve_book_label ──


class TestResolveBookLabel:

    def test_book_label_present(self):
        assert resolve_book_label({"book_label": "刑法学"}) == "刑法学"

    def test_fallback_to_file_name_stem(self):
        assert resolve_book_label({"file_name": "合同法.pdf"}) == "合同法"

    def test_fallback_to_source_stem(self):
        assert resolve_book_label({"source": "/data/宪法教程.txt"}) == "宪法教程"

    def test_all_empty_returns_default(self):
        assert resolve_book_label({}) == "未知资料"

    def test_whitespace_only_book_label_ignored(self):
        assert resolve_book_label({"book_label": "  ", "file_name": "税法.docx"}) == "税法"

    def test_none_values(self):
        assert resolve_book_label({"book_label": None, "file_name": None}) == "未知资料"


# ── collect_book_labels ──


class TestCollectBookLabels:

    def test_deduplicate_and_sort(self):
        docs = [
            Document(page_content="a", metadata={"book_label": "民法"}),
            Document(page_content="b", metadata={"book_label": "刑法"}),
            Document(page_content="c", metadata={"book_label": "民法"}),
        ]
        labels = collect_book_labels(docs)
        assert labels == ["刑法", "民法"]

    def test_empty_docs(self):
        assert collect_book_labels([]) == []

    def test_none_doc_skipped(self):
        docs = [None, Document(page_content="x", metadata={"book_label": "法理"})]
        assert collect_book_labels(docs) == ["法理"]


# ── build_sources ──


class TestBuildSources:

    def test_full_metadata(self):
        doc = Document(
            page_content="...",
            metadata={"book_label": "民法", "chapter": "第三章", "section": "合同", "page": 42},
        )
        sources = build_sources([doc])
        assert len(sources) == 1
        assert "民法" in sources[0]
        assert "章:第三章" in sources[0]
        assert "节:合同" in sources[0]
        assert "页:42" in sources[0]

    def test_no_chapter_section_page(self):
        doc = Document(page_content="...", metadata={"book_label": "刑法"})
        sources = build_sources([doc])
        assert sources == ["刑法"]

    def test_deduplication(self):
        doc1 = Document(page_content="a", metadata={"book_label": "法A", "page": 1})
        doc2 = Document(page_content="b", metadata={"book_label": "法A", "page": 1})
        sources = build_sources([doc1, doc2])
        assert len(sources) == 1

    def test_none_doc_skipped(self):
        sources = build_sources([None, Document(page_content="x", metadata={"book_label": "X"})])
        assert sources == ["X"]


# ── build_context_text ──


class TestBuildContextText:

    def test_basic_output(self):
        docs = [Document(page_content="内容一", metadata={"book_label": "教材A"})]
        text = build_context_text(docs)
        assert "片段1" in text
        assert "教材A" in text
        assert "内容一" in text

    def test_max_docs_limit(self):
        docs = [
            Document(page_content=f"Doc {i}", metadata={"book_label": f"B{i}"})
            for i in range(10)
        ]
        text = build_context_text(docs, max_docs=2)
        assert "片段1" in text
        assert "片段2" in text
        assert "片段3" not in text

    def test_max_chars_limit(self):
        long_content = "A" * 5000
        docs = [
            Document(page_content=long_content, metadata={"book_label": "Big"}),
            Document(page_content="Short", metadata={"book_label": "Small"}),
        ]
        text = build_context_text(docs, max_chars=100)
        # Should only include as many docs as fit within max_chars
        assert "片段1" in text or text == ""

    def test_empty_docs(self):
        assert build_context_text([]) == ""

    def test_none_doc_skipped(self):
        docs = [None, Document(page_content="有效", metadata={"book_label": "X"})]
        text = build_context_text(docs)
        assert "有效" in text
