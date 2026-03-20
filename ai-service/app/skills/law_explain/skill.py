"""概念解释技能配置。"""

from typing import List

from pydantic import BaseModel, Field

from app.skills.skill_config import SkillConfig


class LawExplainOutput(BaseModel):
    """概念解释技能的结构化输出。"""

    definition: str = Field(description="核心概念定义")
    key_points: List[str] = Field(default_factory=list, description="关键要点")
    distinctions: List[str] = Field(default_factory=list, description="易混概念区分")
    pitfalls: List[str] = Field(default_factory=list, description="常见误区")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


def _format(parsed: LawExplainOutput) -> str:
    return (
        f"定义：{parsed.definition}\n"
        f"关键要点：{'; '.join(parsed.key_points) if parsed.key_points else '无'}\n"
        f"概念区分：{'; '.join(parsed.distinctions) if parsed.distinctions else '无'}\n"
        f"常见误区：{'; '.join(parsed.pitfalls) if parsed.pitfalls else '无'}"
    )


config = SkillConfig(
    name="law_explain",
    description="概念解释：用户询问法律概念定义、概念区别、名词解释、理解某个术语",
    output_schema=LawExplainOutput,
    system_prompt=(
        "你是法学课程助教。请把复杂概念解释成可学习、可复盘的结构，"
        "并引导用户回到教材继续探索。"
    ),
    format_answer=_format,
    default_tasks=[
        "回看教材对应章节，提炼3个关键词并解释其关系。",
        "选一个易混概念写对比表（定义、构成、适用）。",
    ],
    confidence_with_docs="medium",
)

from app.skills.skill_agent import RetrievalStrategy, SkillAgent  # noqa: E402

# 概念解释需要广泛检索
retrieval_strategy = RetrievalStrategy(
    k=6,
    use_hyde=True,  # 概念解释最适合 HyDE
)

agent = SkillAgent(config, retrieval_strategy)
