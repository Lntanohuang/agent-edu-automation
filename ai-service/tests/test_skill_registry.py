"""
Tests for skill registry discovery and skill runner.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.skills.registry import discover_skill_configs, get_registered_skills
from app.skills.base import Skill
from app.skills.schemas import SkillResponse


# ── discover_skill_configs ──


class TestDiscoverSkillConfigs:

    def test_discovers_all_expected_skills(self):
        configs = discover_skill_configs()
        expected = {
            "law_article", "case_analysis", "law_explain",
            "assessment_design", "curriculum_outline",
            "knowledge_sequencing", "teaching_activity",
        }
        assert expected.issubset(set(configs.keys())), (
            f"Missing: {expected - set(configs.keys())}"
        )

    def test_each_config_has_required_fields(self):
        configs = discover_skill_configs()
        for name, cfg in configs.items():
            assert cfg.name == name
            assert cfg.description
            assert cfg.system_prompt
            assert cfg.output_schema is not None
            assert callable(cfg.format_answer)
            assert isinstance(cfg.default_tasks, list)


# ── get_registered_skills ──


class TestGetRegisteredSkills:

    def test_returns_skill_instances(self):
        skills = get_registered_skills()
        assert len(skills) >= 7
        for name, skill in skills.items():
            assert isinstance(skill, Skill)
            assert skill.name == name


# ── Skill.run (with mocked LLM) ──


class TestSkillRun:

    @pytest.mark.asyncio
    async def test_run_with_docs(self):
        configs = discover_skill_configs()
        config = configs["law_explain"]

        # Mock the output to match LawExplainOutput schema
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {
            "definition": "定义",
            "key_points": ["要点1"],
            "distinctions": ["区别1"],
            "pitfalls": ["陷阱1"],
            "exploration_tasks": ["任务1", "任务2"],
        }
        # Make isinstance check pass
        mock_output.__class__ = config.output_schema

        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm.with_structured_output.return_value = structured

        skill = Skill(config)
        docs = [Document(page_content="法律条文", metadata={"book_label": "法理学"})]

        with patch("app.skills.base.chat_llm", mock_llm):
            result = await skill.run("什么是法理学", docs)

        assert isinstance(result, SkillResponse)
        assert result.skill_used == "law_explain"
        assert result.confidence == "medium"  # law_explain confidence_with_docs
        assert "法理学" in result.book_labels
        assert len(result.sources) >= 1

    @pytest.mark.asyncio
    async def test_run_without_docs_low_confidence(self):
        configs = discover_skill_configs()
        config = configs["law_article"]

        mock_output = MagicMock()
        mock_output.model_dump.return_value = {
            "conclusion": "结论",
            "legal_basis": [],
            "applicability": "适用性",
            "cautions": [],
            "exploration_tasks": [],
        }
        mock_output.__class__ = config.output_schema
        # Must set exploration_tasks explicitly so getattr returns [] (falsy)
        mock_output.exploration_tasks = []

        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm.with_structured_output.return_value = structured

        skill = Skill(config)

        with patch("app.skills.base.chat_llm", mock_llm):
            result = await skill.run("合同法第52条", [])

        assert result.confidence == "low"  # no docs → confidence_without_docs
        assert result.exploration_tasks == config.default_tasks  # fallback tasks
