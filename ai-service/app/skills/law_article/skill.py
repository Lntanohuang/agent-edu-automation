"""法条解析技能配置。"""

from typing import List

from pydantic import BaseModel, Field

from app.skills.skill_config import SkillConfig


class LawArticleOutput(BaseModel):
    """法条技能的结构化输出。"""

    conclusion: str = Field(description="结论")
    legal_basis: List[str] = Field(default_factory=list, description="条文依据")
    applicability: str = Field(description="适用前提与边界")
    cautions: List[str] = Field(default_factory=list, description="注意事项")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


def _format(parsed: LawArticleOutput) -> str:
    return (
        f"结论：{parsed.conclusion}\n"
        f"适用前提：{parsed.applicability}\n"
        f"条文依据：{'; '.join(parsed.legal_basis) if parsed.legal_basis else '检索结果未明确条文号'}\n"
        f"注意事项：{'; '.join(parsed.cautions) if parsed.cautions else '无'}"
    )


config = SkillConfig(
    name="law_article",
    description="法条解析：用户询问具体法律条文、条文适用条件、构成要件、法条内容",
    output_schema=LawArticleOutput,
    system_prompt=(
        "你是法学检索助教。针对法条型问题，优先给出精确依据。"
        "只可依据给定资料回答；若证据不足请明确说明。"
        "必须给出不少于2条探索任务。"
    ),
    format_answer=_format,
    default_tasks=[
        "回看教材对应章节并整理条文适用前提。",
        "对比相近制度的适用边界并写出差异。",
    ],
    confidence_with_docs="high",
)

from app.skills.skill_agent import RetrievalStrategy, SkillAgent  # noqa: E402

# 法条解析的专属检索策略
retrieval_strategy = RetrievalStrategy(
    k=4,  # 精确查询不需要太多文档
    bm25_weight_override=0.7,  # 重 BM25，精确匹配优先
    metadata_filters={"doc_type": "statute"},
    use_hyde=False,  # 法条查询不需要 HyDE
)

agent = SkillAgent(config, retrieval_strategy)
