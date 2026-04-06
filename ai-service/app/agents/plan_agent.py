"""
多技能编排教案生成 Agent。

流程：检索教材 → 调用 skills 获取领域知识 → 综合生成完整学期教案。
"""

import asyncio
import time
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_traced_logger
from app.llm.model_factory import chat_llm
from app.retrieval.query_analyzer import analyze_query
from app.retrieval.hybrid_retriever import get_hybrid_retriever
from app.prompts.plan_prompts import lesson_plan_prompt
from app.skills.registry import get_registered_skills

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
        logger = get_traced_logger("plan_agent")
        trace_id = str(inputs.get("trace_id") or "-") if isinstance(inputs, dict) else "-"
        started_at = time.time()
        messages = inputs.get("messages", []) if isinstance(inputs, dict) else []
        user_query = ""
        if messages:
            last_msg = messages[-1]
            user_query = str(getattr(last_msg, "content", "") or "")
        if not user_query:
            raise ValueError("缺少用户输入")
        logger.info("plan_agent_started", trace_id=trace_id, query_chars=len(user_query))

        # ── 1. 检索教材文档（混合检索） ──
        retrieval_started_at = time.time()
        hybrid_retriever = get_hybrid_retriever()
        analysis = analyze_query(user_query)
        retrieved_docs = hybrid_retriever.retrieve(user_query, analysis, k=8)
        logger.info(
            "plan_agent_retrieval_done",
            trace_id=trace_id,
            intent=analysis.intent,
            retrieved_doc_count=len(retrieved_docs),
            elapsed_ms=round((time.time() - retrieval_started_at) * 1000, 1),
        )

        # ── 2. 调用 skills 获取领域知识 ──
        all_skills = get_registered_skills()
        skill_insights: list[str] = []

        async def _run_skill(name: str, skill, query: str, docs):
            try:
                result = await skill.run(query, docs)
                logger.info("plan_agent_skill_succeeded", skill=name)
                return name, result
            except Exception as exc:
                logger.error("plan_agent_skill_failed", skill=name, error=str(exc), exc_info=True)
                return name, None

        tasks = []
        for skill_name in _PLAN_SKILLS:
            skill = all_skills.get(skill_name)
            if skill is None:
                logger.warning("plan_agent_skill_not_registered", skill=skill_name)
                continue
            tasks.append(_run_skill(skill_name, skill, user_query, retrieved_docs))

        skills_started_at = time.time()
        results = await asyncio.gather(*tasks)
        success_skills = 0
        failed_skills: list[str] = []
        for name, result in results:
            if result:
                skill_insights.append(f"=== {name} ===\n{result.answer}")
                success_skills += 1
            else:
                failed_skills.append(name)
        logger.info(
            "plan_agent_skills_done",
            trace_id=trace_id,
            success_count=success_skills,
            failed_count=len(failed_skills),
            failed_skills=failed_skills,
            elapsed_ms=round((time.time() - skills_started_at) * 1000, 1),
        )

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

        # ── 4. 最终 LLM 生成（教案需要更大的 max_tokens） ──
        plan_llm = chat_llm.bind(max_tokens=settings.plan_agent_max_tokens)
        structured_llm = plan_llm.with_structured_output(
            SemesterPlanOutput,
            method="json_schema",
        )

        llm_started_at = time.time()
        try:
            structured = await structured_llm.ainvoke([
                SystemMessage(content=lesson_plan_prompt),
                HumanMessage(content=enriched_query),
            ])
        except Exception as exc:
            logger.error("plan_agent_llm_failed", trace_id=trace_id, error=str(exc), exc_info=True)
            raise LLMError(f"教案生成 LLM 调用失败: {exc}", detail={"trace_id": trace_id}) from exc
        logger.info(
            "plan_agent_llm_done",
            trace_id=trace_id,
            elapsed_ms=round((time.time() - llm_started_at) * 1000, 1),
        )
        logger.info(
            "plan_agent_completed",
            trace_id=trace_id,
            total_elapsed_ms=round((time.time() - started_at) * 1000, 1),
        )

        return {"structured_response": structured}


def create_plan_agent():
    """创建多技能编排教案生成 Agent。"""
    return SkillEnhancedPlanAgent()
