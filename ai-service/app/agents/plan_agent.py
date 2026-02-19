from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from app.llm.model_factory import ollama_qwen_llm
from app.prompts.plan_prompts import lesson_plan_prompt
from app.tools.rag_tool import retrieve_context

from pydantic import BaseModel, Field


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


class TwoStagePlanAgent:
    """
    Two-stage plan agent:
    1) Retrieve context by tool.
    2) Generate structured output with model.with_structured_output.
    """

    async def ainvoke(self, inputs: dict) -> dict:
        messages = inputs.get("messages", []) if isinstance(inputs, dict) else []
        user_query = ""
        if messages:
            last_msg = messages[-1]
            user_query = str(getattr(last_msg, "content", "") or "")
        if not user_query:
            raise ValueError("缺少用户输入")

        tool_result = retrieve_context.invoke({"query": user_query})
        if isinstance(tool_result, tuple):
            context_text = str(tool_result[0] or "")
        else:
            context_text = str(tool_result or "")

        structured_llm = ollama_qwen_llm.with_structured_output(
            SemesterPlanOutput,
            method="json_schema",
        )

        enriched_query = (
            f"{user_query}\n\n"
            f"可参考检索上下文：\n{context_text}\n\n"
            "请严格按结构化字段输出。"
        )

        structured = await structured_llm.ainvoke(
            [
                SystemMessage(content=lesson_plan_prompt),
                HumanMessage(content=enriched_query),
            ]
        )

        return {"structured_response": structured}


def create_plan_agent():
    """
    创建两段式教案生成 Agent（先检索，再结构化输出）。
    """
    return TwoStagePlanAgent()
