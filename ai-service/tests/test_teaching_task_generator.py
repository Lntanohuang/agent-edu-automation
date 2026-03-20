"""
Tests for TeachingTaskGeneratorSkill.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.skills.teaching_task_generator.skill import (
    TeachingTaskGeneratorSkill,
    TeachingTasksOutput,
)


@pytest.fixture()
def skill():
    return TeachingTaskGeneratorSkill()


class TestTeachingTaskGeneratorSkill:

    @pytest.mark.asyncio
    async def test_short_circuits_when_enough_existing_tasks(self, skill):
        existing = ["任务A", "任务B", "任务C", "任务D"]
        result = await skill.run(
            query="问题",
            answer="回答",
            retrieved_docs=[],
            existing_tasks=existing,
        )
        # Should return existing[:3] without calling LLM
        assert result == ["任务A", "任务B", "任务C"]

    @pytest.mark.asyncio
    async def test_generates_tasks_via_llm(self, skill):
        mock_output = TeachingTasksOutput(tasks=["生成任务1", "生成任务2"])

        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm.with_structured_output.return_value = structured

        docs = [Document(page_content="教材内容", metadata={"book_label": "合同法"})]

        with patch("app.skills.teaching_task_generator.skill.chat_llm", mock_llm):
            result = await skill.run(
                query="什么是合同",
                answer="合同是...",
                retrieved_docs=docs,
                existing_tasks=[],
            )
        assert result == ["生成任务1", "生成任务2"]

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, skill):
        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(side_effect=RuntimeError("LLM error"))
        mock_llm.with_structured_output.return_value = structured

        docs = [Document(page_content="内容", metadata={"book_label": "民法"})]

        with patch("app.skills.teaching_task_generator.skill.chat_llm", mock_llm):
            result = await skill.run(
                query="问题",
                answer="回答",
                retrieved_docs=docs,
                existing_tasks=[],
            )
        # Should return fallback tasks
        assert len(result) == 3
        assert "民法" in result[0]

    @pytest.mark.asyncio
    async def test_fallback_no_docs(self, skill):
        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(side_effect=RuntimeError("fail"))
        mock_llm.with_structured_output.return_value = structured

        with patch("app.skills.teaching_task_generator.skill.chat_llm", mock_llm):
            result = await skill.run(
                query="q", answer="a", retrieved_docs=[], existing_tasks=[],
            )
        assert len(result) == 3
        assert "教材" in result[0]  # fallback label when no docs

    @pytest.mark.asyncio
    async def test_exactly_two_existing_tasks_short_circuits(self, skill):
        existing = ["任务X", "任务Y"]
        result = await skill.run(
            query="q", answer="a", retrieved_docs=[], existing_tasks=existing,
        )
        assert result == ["任务X", "任务Y"]
