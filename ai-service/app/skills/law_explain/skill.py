import re
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm.model_factory import ollama_qwen_llm
from app.skills.base import SkillBase, build_context_text, build_sources, collect_book_labels
from app.skills.schemas import SkillResponse


class LawExplainOutput(BaseModel):
    definition: str = Field(description="核心概念定义")
    key_points: List[str] = Field(default_factory=list, description="关键要点")
    distinctions: List[str] = Field(default_factory=list, description="易混概念区分")
    pitfalls: List[str] = Field(default_factory=list, description="常见误区")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


class LawExplainSkill(SkillBase):
    name = "law_explain"

    def can_handle(self, query: str) -> bool:
        patterns = [
            r"是什么",
            r"区别",
            r"概念",
            r"解释",
            r"怎么理解",
        ]
        return any(re.search(pattern, query) for pattern in patterns)

    async def run(self, query: str, retrieved_docs: List[Document]) -> SkillResponse:
        context_text = build_context_text(retrieved_docs)
        llm = ollama_qwen_llm.with_structured_output(LawExplainOutput, method="json_schema")
        output = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是法学课程助教。请把复杂概念解释成可学习、可复盘的结构，"
                        "并引导用户回到教材继续探索。"
                    )
                ),
                HumanMessage(
                    content=(
                        f"用户问题：{query}\n\n"
                        f"检索上下文：\n{context_text}\n\n"
                        "请输出结构化结果。"
                    )
                ),
            ]
        )
        parsed = output if isinstance(output, LawExplainOutput) else LawExplainOutput.model_validate(output)
        answer = (
            f"定义：{parsed.definition}\n"
            f"关键要点：{'; '.join(parsed.key_points) if parsed.key_points else '无'}\n"
            f"概念区分：{'; '.join(parsed.distinctions) if parsed.distinctions else '无'}\n"
            f"常见误区：{'; '.join(parsed.pitfalls) if parsed.pitfalls else '无'}"
        )
        tasks = parsed.exploration_tasks[:3] if parsed.exploration_tasks else [
            "回看教材对应章节，提炼3个关键词并解释其关系。",
            "选一个易混概念写对比表（定义、构成、适用）。",
        ]
        return SkillResponse(
            skill_used=self.name,
            answer=answer,
            sources=build_sources(retrieved_docs),
            book_labels=collect_book_labels(retrieved_docs),
            exploration_tasks=tasks,
            confidence="medium" if retrieved_docs else "low",
        )
