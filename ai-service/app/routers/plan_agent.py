"""
教案 Agent 路由
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agents import create_plan_agent
from app.agents.plan_agent import SemesterPlanOutput
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
plan_agent = create_plan_agent()


class PlanAgentGenerateRequest(BaseModel):
    subject: str = Field(..., description="学科")
    grade: str = Field(default="无", description="年级")
    topic: str = Field(default="课程主题", description="学期主题/核心单元")
    total_weeks: int = Field(default=18, ge=8, le=24, description="学期周数")
    lessons_per_week: int = Field(default=2, ge=1, le=8, description="每周课时")
    class_size: int = Field(default=40, ge=1, le=100, description="班级人数")
    teaching_goals: Optional[str] = Field(default="掌握本课核心知识与基本应用", description="教学目标")
    requirements: Optional[str] = Field(default="无", description="特殊要求")
    textbook_version: Optional[str] = Field(default="通用版", description="教材版本")
    difficulty: Optional[str] = Field(default="中等", description="难度")


class PlanAgentGenerateResponse(BaseModel):
    success: bool = True
    message: str = "生成成功"
    semester_plan: Dict[str, Any]


@router.post("/generate", response_model=PlanAgentGenerateResponse)
async def generate_lesson_plan_by_agent(request: PlanAgentGenerateRequest):
    """
    使用教案 Agent 生成结构化整学期教案
    """
    user_query = (
        f"请生成一份整学期教案规划。"
        f"\n学科：{request.subject}"
        f"\n年级：{request.grade}"
        f"\n学期主题：{request.topic}"
        f"\n学期周数：{request.total_weeks}"
        f"\n每周课时：{request.lessons_per_week}"
        f"\n班级人数：{request.class_size}"
        f"\n教材版本：{request.textbook_version or '未指定'}"
        f"\n难度：{request.difficulty or '中等'}"
        f"\n教学目标：{request.teaching_goals or '未指定'}"
        f"\n特殊要求：{request.requirements or '无'}"
        f"\n必须输出覆盖整个学期每周安排。"
        f"\n请严格按结构化字段输出。"
    )

    try:
        result = await plan_agent.ainvoke({"messages": [HumanMessage(content=user_query)]})
        structured = result.get("structured_response") if isinstance(result, dict) else None

        if isinstance(structured, SemesterPlanOutput):
            semester_plan = structured.model_dump()
        elif isinstance(structured, dict):
            semester_plan = structured
        else:
            raise ValueError("Agent 未返回 structured_response")

        return PlanAgentGenerateResponse(
            success=True,
            message="生成成功",
            semester_plan=semester_plan,
        )
    except Exception as exc:
        logger.error("Plan agent generate failed", error=str(exc))
        return PlanAgentGenerateResponse(
            success=False,
            message=f"生成失败: {str(exc)}",
            semester_plan={},
        )
