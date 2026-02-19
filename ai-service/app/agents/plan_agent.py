from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from app.llm.model_factory import ollama_qwen_llm
from app.prompts.plan_prompts import lesson_plan_prompt
from app.tools.rag_tool import retrieve_context

from pydantic import BaseModel, Field


class LessonPlanOutput(BaseModel):
    """Final structured output for lesson plan generation."""
    title: str = Field(description="Lesson plan title")
    subject: str = Field(description="Subject")
    grade: str = Field(description="Grade level")
    duration: int = Field(description="Number of class periods")
    objectives: List[str] = Field(description="Teaching objectives")
    key_points: List[str] = Field(description="Key teaching points")
    difficulties: List[str] = Field(description="Teaching difficulties")
    teaching_methods: List[str] = Field(description="Teaching methods")
    teaching_aids: List[str] = Field(description="Teaching aids")
    procedures: List[dict] = Field(description="Teaching procedures with stage/duration/content/activities/design_intent")
    homework: str = Field(description="Homework assignment")
    blackboard_design: str = Field(description="Blackboard design")
    reflection_guide: str = Field(description="Post-class reflection guide")
    resources: List[dict] = Field(description="Recommended resources with title/type/description")


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
            LessonPlanOutput,
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
