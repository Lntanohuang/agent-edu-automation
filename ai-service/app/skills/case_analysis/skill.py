"""案例分析技能配置。"""

from typing import List

from pydantic import BaseModel, Field

from app.skills.skill_config import SkillConfig


class CaseAnalysisOutput(BaseModel):
    """案例分析技能的结构化输出。"""

    fact_summary: str = Field(description="案情事实总结")
    issues: List[str] = Field(default_factory=list, description="争议焦点")
    rule_application: str = Field(description="规则适用分析")
    conclusion: str = Field(description="分析结论")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


def _format(parsed: CaseAnalysisOutput) -> str:
    return (
        f"事实：{parsed.fact_summary}\n"
        f"争点：{'; '.join(parsed.issues) if parsed.issues else '未识别'}\n"
        f"规则适用：{parsed.rule_application}\n"
        f"结论：{parsed.conclusion}"
    )


config = SkillConfig(
    name="case_analysis",
    description="案例分析：用户描述案情、询问判决结果、讨论争议焦点、分析案例",
    output_schema=CaseAnalysisOutput,
    system_prompt=(
        "你是法学案例分析助教。请按 事实-争点-规则适用-结论 结构回答，"
        "并提供可执行的后续探索任务。"
    ),
    format_answer=_format,
    default_tasks=[
        "从教材中找一个相反结论案例并比较差异。",
        "列出本案结论成立的关键事实条件。",
    ],
    confidence_with_docs="high",
)
