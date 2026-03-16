"""
多技能编排教案生成 Agent。

流程：检索教材 → 调用 skills 获取领域知识 → 综合生成完整学期教案。
"""

import asyncio
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm.model_factory import chat_llm
from app.llm.vector_store import get_rag_vector_store
from app.prompts.plan_prompts import lesson_plan_prompt
from app.skills.registry import get_registered_skills

logger = logging.getLogger(__name__)

# Plan Agent 依赖的 skill 名称（按调用顺序）
_PLAN_SKILLS = [
    "curriculum_outline",
    "knowledge_sequencing",
    "teaching_activity",
    "assessment_design",
]


class WeeklyPlan(BaseModel):
    week: int = Field(description="Week number starting from 1")
    unit_topic: str = Field(description="Weekly unit topic")
    objectives: List[str] = Field(description="Weekly objectives")
    key_points: List[str] = Field(description="Weekly key points")
    difficulties: List[str] = Field(description="Weekly difficulties")
    activities: List[str] = Field(description="Weekly core activities")
    homework: str = Field(description="Weekly homework")
    assessment: str = Field(description="Weekly assessment method")


class SemesterPlanOutput(BaseModel):
    """Final structured output for semester lesson plan generation."""
    semester_title: str = Field(description="Semester plan title")
    subject: str = Field(description="Subject")
    grade: str = Field(description="Grade level")
    total_weeks: int = Field(description="Total weeks in semester")
    lessons_per_week: int = Field(description="Lessons per week")
    textbook_version: str = Field(description="Textbook version")
    difficulty: str = Field(description="Difficulty level")
    semester_goals: List[str] = Field(description="Semester-level goals")
    key_competencies: List[str] = Field(description="Core competencies to cultivate")
    teaching_strategies: List[str] = Field(description="Semester teaching strategies")
    weekly_plans: List[WeeklyPlan] = Field(description="Weekly teaching plans")
    assessment_plan: List[str] = Field(description="Semester assessment plan")
    resource_plan: List[str] = Field(description="Semester teaching resource plan")


class SkillEnhancedPlanAgent:
    """
    多技能编排教案 Agent：

    1. 检索教材文档
    2. 依次调用 curriculum_outline / knowledge_sequencing /
       teaching_activity / assessment_design skills
    3. 将 skills 输出作为增强上下文注入最终 prompt
    4. LLM 生成完整学期教案
    """

    async def ainvoke(self, inputs: dict) -> dict:
        messages = inputs.get("messages", []) if isinstance(inputs, dict) else []
        user_query = ""
        if messages:
            last_msg = messages[-1]
            user_query = str(getattr(last_msg, "content", "") or "")
        if not user_query:
            raise ValueError("缺少用户输入")

        # ── 1. 检索教材文档 ──
        vector_store = get_rag_vector_store()
        retrieved_docs = vector_store.similarity_search(user_query, k=8)

        # ── 2. 调用 skills 获取领域知识 ──
        all_skills = get_registered_skills()
        skill_insights: list[str] = []

        async def _run_skill(name: str, skill, query: str, docs):
            try:
                result = await skill.run(query, docs)
                logger.info("Plan Agent skill 调用成功: %s", name)
                return name, result
            except Exception:
                logger.exception("Plan Agent skill 调用失败: %s", name)
                return name, None

        tasks = []
        for skill_name in _PLAN_SKILLS:
            skill = all_skills.get(skill_name)
            if skill is None:
                logger.warning("Plan Agent 所需技能未注册: %s", skill_name)
                continue
            tasks.append(_run_skill(skill_name, skill, user_query, retrieved_docs))

        results = await asyncio.gather(*tasks)
        for name, result in results:
            if result:
                skill_insights.append(f"=== {name} ===\n{result.answer}")

        # ── 3. 组装增强 prompt ──
        skills_context = "\n\n".join(skill_insights) if skill_insights else ""

        enriched_query_parts = [user_query]
        if skills_context:
            enriched_query_parts.append(
                f"以下是教学设计专家从教材中提取的参考信息，请据此生成更精准的教案：\n\n"
                f"{skills_context}"
            )
        enriched_query_parts.append("请严格按结构化字段输出。")
        enriched_query = "\n\n".join(enriched_query_parts)

        # ── 4. 最终 LLM 生成 ──
        structured_llm = chat_llm.with_structured_output(
            SemesterPlanOutput,
            method="json_schema",
        )

        structured = await structured_llm.ainvoke([
            SystemMessage(content=lesson_plan_prompt),
            HumanMessage(content=enriched_query),
        ])

        return {"structured_response": structured}


def create_plan_agent():
    """创建多技能编排教案生成 Agent。"""
    return SkillEnhancedPlanAgent()
