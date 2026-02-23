"""案例分析技能：按事实-争点-规则适用-结论作答。"""

import re
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm.model_factory import ollama_qwen_llm
from app.skills.base import SkillBase, build_context_text, build_sources, collect_book_labels
from app.skills.schemas import SkillResponse


class CaseAnalysisOutput(BaseModel):
    """案例分析技能的结构化输出。"""

    fact_summary: str = Field(description="案情事实总结")
    issues: List[str] = Field(default_factory=list, description="争议焦点")
    rule_application: str = Field(description="规则适用分析")
    conclusion: str = Field(description="分析结论")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


class CaseAnalysisSkill(SkillBase):
    """面向案例类问题的技能实现。"""

    name = "case_analysis"

    def can_handle(self, query: str) -> bool:
        """根据关键词判断是否命中案例场景。"""
        patterns = [
            r"案例",
            r"案情",
            r"如何判",
            r"判决",
            r"争议焦点",
        ]
        return any(re.search(pattern, query) for pattern in patterns)

    async def run(self, query: str, retrieved_docs: List[Document]) -> SkillResponse:
        """执行案例分析并返回统一技能结果。"""
        context_text = build_context_text(retrieved_docs)
        llm = ollama_qwen_llm.with_structured_output(CaseAnalysisOutput, method="json_schema")
        output = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是法学案例分析助教。请按 事实-争点-规则适用-结论 结构回答，"
                        "并提供可执行的后续探索任务。"
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
        parsed = output if isinstance(output, CaseAnalysisOutput) else CaseAnalysisOutput.model_validate(output)
        answer = (
            f"事实：{parsed.fact_summary}\n"
            f"争点：{'; '.join(parsed.issues) if parsed.issues else '未识别'}\n"
            f"规则适用：{parsed.rule_application}\n"
            f"结论：{parsed.conclusion}"
        )
        tasks = parsed.exploration_tasks[:3] if parsed.exploration_tasks else [
            "从教材中找一个相反结论案例并比较差异。",
            "列出本案结论成立的关键事实条件。",
        ]
        return SkillResponse(
            skill_used=self.name,
            answer=answer,
            sources=build_sources(retrieved_docs),
            book_labels=collect_book_labels(retrieved_docs),
            exploration_tasks=tasks,
            confidence="high" if retrieved_docs else "low",
        )
