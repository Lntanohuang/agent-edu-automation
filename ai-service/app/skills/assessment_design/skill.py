"""考核方案设计技能配置。"""

from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator

from app.skills.skill_config import SkillConfig


class AssessmentItem(BaseModel):
    """单个考核项目。"""
    name: str = Field(description="考核项目名称")
    category: str = Field(description="类别：formative（形成性）或 summative（终结性）")
    weight: int = Field(description="占总成绩百分比")
    description: str = Field(description="考核方式说明")
    timing: str = Field(description="实施时间点（如第4周、期末）")


class AssessmentDesignOutput(BaseModel):
    """考核方案设计的结构化输出。"""

    course_objectives_summary: str = Field(default="", description="考核对应的教学目标概述")
    formative_items: List[AssessmentItem] = Field(default_factory=list, description="形成性评价项目")
    summative_items: List[AssessmentItem] = Field(default_factory=list, description="终结性评价项目")
    weight_distribution: str = Field(default="", description="成绩权重分配说明")
    rubric_notes: List[str] = Field(default_factory=list, description="评分标准要点")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")

    @model_validator(mode="before")
    @classmethod
    def unwrap_nested(cls, data):
        """qwen-plus 可能将输出包裹在容器对象中，自动展开。"""
        if isinstance(data, dict) and len(data) == 1:
            key = next(iter(data))
            inner = data[key]
            if isinstance(inner, dict) and key not in cls.model_fields:
                return inner
        return data

    @field_validator("formative_items", "summative_items", mode="before")
    @classmethod
    def coerce_assessment_items(cls, v):
        if isinstance(v, list):
            return [
                {"name": item, "category": "", "weight": 0, "description": item, "timing": ""}
                if isinstance(item, str) else item
                for item in v
            ]
        return v


def _format(parsed: AssessmentDesignOutput) -> str:
    formative = "\n".join(
        f"  - {a.name}（{a.weight}%，{a.timing}）：{a.description}"
        for a in parsed.formative_items
    ) if parsed.formative_items else "  暂无"
    summative = "\n".join(
        f"  - {a.name}（{a.weight}%，{a.timing}）：{a.description}"
        for a in parsed.summative_items
    ) if parsed.summative_items else "  暂无"
    return (
        f"教学目标：{parsed.course_objectives_summary}\n"
        f"形成性评价：\n{formative}\n"
        f"终结性评价：\n{summative}\n"
        f"权重分配：{parsed.weight_distribution}\n"
        f"评分标准：{'; '.join(parsed.rubric_notes) if parsed.rubric_notes else '待制定'}"
    )


config = SkillConfig(
    name="assessment_design",
    description="考核方案设计：根据课程目标设计形成性评价和终结性评价方案，含权重分配和评分标准",
    output_schema=AssessmentDesignOutput,
    system_prompt=(
        "你是教学评价专家。请根据给定课程内容设计多元化考核方案。"
        "方案应包含形成性评价（过程性考核）和终结性评价（期末考核），"
        "并给出各项权重分配和评分标准要点。"
        "注意考核方式应与教学目标对齐，避免单一化。"
        "输出必须是扁平 JSON，顶层字段为：course_objectives_summary, formative_items, summative_items, weight_distribution, rubric_notes, exploration_tasks。不要嵌套在其他对象中。"
    ),
    format_answer=_format,
    default_tasks=[
        "对照布鲁姆认知目标分类检查考核覆盖度。",
        "设计一份形成性评价的具体评分量表。",
    ],
    confidence_with_docs="medium",
)

from app.skills.skill_agent import RetrievalStrategy, SkillAgent  # noqa: E402

agent = SkillAgent(config)
