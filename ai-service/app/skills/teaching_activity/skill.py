"""教学活动设计技能配置。"""

from typing import List

from pydantic import BaseModel, Field

from app.skills.skill_config import SkillConfig


class ActivityItem(BaseModel):
    """单个教学活动。"""
    name: str = Field(description="活动名称")
    activity_type: str = Field(description="活动类型（如案例研讨、小组讨论、实验、角色扮演、翻转课堂）")
    duration: str = Field(description="建议时长（如15分钟、1课时）")
    description: str = Field(description="活动具体描述")
    materials: List[str] = Field(default_factory=list, description="所需材料或资源")


class TeachingActivityOutput(BaseModel):
    """教学活动设计的结构化输出。"""

    topic_context: str = Field(description="活动针对的知识点或教学主题")
    activities: List[ActivityItem] = Field(default_factory=list, description="推荐的教学活动列表")
    pedagogical_rationale: str = Field(description="教学法依据（为何选择这些活动）")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


def _format(parsed: TeachingActivityOutput) -> str:
    activities_text = "\n".join(
        f"  {i}. [{a.activity_type}] {a.name}（{a.duration}）：{a.description}"
        for i, a in enumerate(parsed.activities, 1)
    ) if parsed.activities else "  暂无建议"
    return (
        f"教学主题：{parsed.topic_context}\n"
        f"推荐活动：\n{activities_text}\n"
        f"教学法依据：{parsed.pedagogical_rationale}"
    )


config = SkillConfig(
    name="teaching_activity",
    description="教学活动设计：根据知识点推荐课堂活动（案例研讨、小组讨论、实验、角色扮演等）",
    output_schema=TeachingActivityOutput,
    system_prompt=(
        "你是教学设计专家。请根据给定的知识点和教材内容，推荐3-5个具体可执行的课堂教学活动。"
        "每个活动需说明类型、时长、描述和所需材料。"
        "活动应多样化，覆盖不同教学法（讲授、互动、实践）。"
    ),
    format_answer=_format,
    default_tasks=[
        "针对学生反馈调整活动难度和互动方式。",
        "为每个活动设计配套的课前预习任务。",
    ],
    confidence_with_docs="medium",
)

from app.skills.skill_agent import RetrievalStrategy, SkillAgent  # noqa: E402

agent = SkillAgent(config)
