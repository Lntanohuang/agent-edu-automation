"""
Tests for skill router (select_skill).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.skills.base import Skill
from app.skills.router import RouteDecision, _build_routing_prompt, select_skill


class TestBuildRoutingPrompt:

    def test_includes_skill_names(self):
        from app.skills.registry import get_registered_skills
        skills = get_registered_skills()
        prompt = _build_routing_prompt(skills)
        assert "law_article" in prompt
        assert "law_explain" in prompt
        assert "case_analysis" in prompt
        assert "技能路由器" in prompt


class TestSelectSkill:

    @pytest.mark.asyncio
    async def test_routes_to_correct_skill(self):
        decision = RouteDecision(skill_name="case_analysis", reason="涉及案例分析")

        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(return_value=decision)
        mock_llm.with_structured_output.return_value = structured

        with patch("app.skills.router.chat_llm", mock_llm):
            # Reset cached skills
            import app.skills.router as router_mod
            router_mod._skills = {}
            skill = await select_skill("分析张三诉李四案")

        assert skill.name == "case_analysis"

    @pytest.mark.asyncio
    async def test_fallback_on_unknown_skill(self):
        decision = RouteDecision(skill_name="nonexistent", reason="???")

        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(return_value=decision)
        mock_llm.with_structured_output.return_value = structured

        with patch("app.skills.router.chat_llm", mock_llm):
            import app.skills.router as router_mod
            router_mod._skills = {}
            from app.skills.registry import get_registered_skills
            skill = await select_skill("随便的问题")

        # fallback 改为相似度匹配，返回注册技能之一即可
        assert skill.name in get_registered_skills()

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self):
        mock_llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))
        mock_llm.with_structured_output.return_value = structured

        with patch("app.skills.router.chat_llm", mock_llm):
            import app.skills.router as router_mod
            router_mod._skills = {}
            from app.skills.registry import get_registered_skills
            skill = await select_skill("任何问题")

        # fallback 改为相似度匹配，返回注册技能之一即可
        assert skill.name in get_registered_skills()
