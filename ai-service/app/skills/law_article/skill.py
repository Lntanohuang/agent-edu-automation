"""法条解析技能：聚焦条文依据与适用边界。"""

import re
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm.model_factory import ollama_qwen_llm
from app.skills.base import SkillBase, build_context_text, build_sources, collect_book_labels
from app.skills.schemas import SkillResponse


class LawArticleOutput(BaseModel):
    """法条技能的结构化输出。"""

    conclusion: str = Field(description="结论")
    legal_basis: List[str] = Field(default_factory=list, description="条文依据")
    applicability: str = Field(description="适用前提与边界")
    cautions: List[str] = Field(default_factory=list, description="注意事项")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


class LawArticleSkill(SkillBase):
    """面向法条/构成要件类问题的技能实现。"""

    name = "law_article"

    def can_handle(self, query: str) -> bool:
        """根据关键词判断是否命中法条场景。"""
        patterns = [
            r"第\s*\d+\s*条",
            r"法条",
            r"条文",
            r"适用",
            r"构成要件",
        ]
        return any(re.search(pattern, query) for pattern in patterns)

    async def run(self, query: str, retrieved_docs: List[Document]) -> SkillResponse:
        """执行法条分析并返回统一技能结果。"""
        context_text = build_context_text(retrieved_docs)
        llm = ollama_qwen_llm.with_structured_output(LawArticleOutput, method="json_schema")
        output = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是法学检索助教。针对法条型问题，优先给出精确依据。"
                        "只可依据给定资料回答；若证据不足请明确说明。"
                        "必须给出不少于2条探索任务。"
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
        parsed = output if isinstance(output, LawArticleOutput) else LawArticleOutput.model_validate(output)
        answer = (
            f"结论：{parsed.conclusion}\n"
            f"适用前提：{parsed.applicability}\n"
            f"条文依据：{'; '.join(parsed.legal_basis) if parsed.legal_basis else '检索结果未明确条文号'}\n"
            f"注意事项：{'; '.join(parsed.cautions) if parsed.cautions else '无'}"
        )
        tasks = parsed.exploration_tasks[:3] if parsed.exploration_tasks else [
            "回看教材对应章节并整理条文适用前提。",
            "对比相近制度的适用边界并写出差异。",
        ]
        return SkillResponse(
            skill_used=self.name,
            answer=answer,
            sources=build_sources(retrieved_docs),
            book_labels=collect_book_labels(retrieved_docs),
            exploration_tasks=tasks,
            confidence="high" if retrieved_docs else "low",
        )
