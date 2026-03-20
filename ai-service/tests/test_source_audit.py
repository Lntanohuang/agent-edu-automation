"""
Tests for SourceAuditSkill — sync, no mocking needed.
"""
import pytest
from langchain_core.documents import Document

from app.skills.source_audit.skill import SourceAuditResult, SourceAuditSkill


@pytest.fixture()
def skill():
    return SourceAuditSkill()


class TestSourceAuditSkill:

    def test_high_confidence_with_sources_and_docs(self, skill):
        result = skill.run(
            answer="合同法第52条规定……",
            sources=["合同法 (页:52)"],
            retrieved_docs=[Document(page_content="片段", metadata={})],
        )
        assert isinstance(result, SourceAuditResult)
        assert result.confidence == "high"
        assert result.audited_answer == "合同法第52条规定……"
        assert any("来源核对" in n for n in result.source_notes)

    def test_medium_confidence_docs_but_no_sources(self, skill):
        result = skill.run(
            answer="回答内容",
            sources=[],
            retrieved_docs=[Document(page_content="有文档", metadata={})],
        )
        assert result.confidence == "medium"
        assert "来源提示" in result.audited_answer
        assert any("来源标签缺失" in n for n in result.source_notes)

    def test_low_confidence_no_docs_no_sources(self, skill):
        result = skill.run(
            answer="猜测回答",
            sources=[],
            retrieved_docs=[],
        )
        assert result.confidence == "low"
        assert "证据不足" in result.audited_answer
        assert any("未检索到" in n for n in result.source_notes)

    def test_low_confidence_sources_but_no_docs(self, skill):
        """sources 列表非空但 retrieved_docs 为空 → 仍然 low"""
        result = skill.run(
            answer="回答",
            sources=["某来源"],
            retrieved_docs=[],
        )
        # has_sources=True, has_docs=False → falls into else branch
        assert result.confidence == "low"
