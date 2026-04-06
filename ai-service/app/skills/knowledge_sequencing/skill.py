"""知识点编排技能配置。"""

from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator

from app.skills.skill_config import SkillConfig


class SequencedTopic(BaseModel):
    """编排后的单个知识点条目。"""
    week_range: str = Field(description="建议教学周（如1-2、3、4-5）")
    topic: str = Field(description="知识点或单元主题")
    level: str = Field(description="认知层次：基础/核心/进阶")
    depends_on: List[str] = Field(default_factory=list, description="前置依赖知识点")
    learning_objectives: List[str] = Field(default_factory=list, description="该知识点的学习目标")


class KnowledgeSequencingOutput(BaseModel):
    """知识点编排的结构化输出。"""

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

    @field_validator("sequenced_topics", mode="before")
    @classmethod
    def coerce_sequenced_topics(cls, v):
        if isinstance(v, list):
            return [
                {"topic": item, "week_range": "", "level": "基础", "depends_on": [], "learning_objectives": []}
                if isinstance(item, str) else item
                for item in v
            ]
        return v

    sequencing_rationale: str = Field(default="", description="编排逻辑说明（为何如此排序）")
    sequenced_topics: List[SequencedTopic] = Field(default_factory=list, description="按教学顺序排列的知识点")
    milestone_weeks: List[str] = Field(default_factory=list, description="关键节点周（如复习周、实践周）")
    exploration_tasks: List[str] = Field(default_factory=list, description="后续探索任务")


def _format(parsed: KnowledgeSequencingOutput) -> str:
    topics_text = "\n".join(
        f"  第{t.week_range}周 [{t.level}] {t.topic}"
        + (f"（依赖：{', '.join(t.depends_on)}）" if t.depends_on else "")
        for t in parsed.sequenced_topics
    ) if parsed.sequenced_topics else "  未编排"
    return (
        f"编排逻辑：{parsed.sequencing_rationale}\n"
        f"教学顺序：\n{topics_text}\n"
        f"关键节点：{'; '.join(parsed.milestone_weeks) if parsed.milestone_weeks else '无'}"
    )


config = SkillConfig(
    name="knowledge_sequencing",
    description="知识点编排：将知识点按认知难度排序，设计递进式学习路径（前置→核心→进阶），标注依赖关系",
    output_schema=KnowledgeSequencingOutput,
    system_prompt=(
        "你是课程设计专家。请将给定的知识点按照认知难度递进排序，"
        "设计合理的教学顺序。标注每个知识点的认知层次（基础/核心/进阶）"
        "和前置依赖关系。安排应遵循由浅入深、螺旋上升的教学原则。"
        "同时标注关键节点周（复习、实践、阶段测试）。"
        "\n输出必须是扁平 JSON，顶层字段为：sequencing_rationale, sequenced_topics, milestone_weeks, exploration_tasks。不要嵌套在其他对象中。"
    ),
    format_answer=_format,
    default_tasks=[
        "检查知识点依赖关系是否形成合理的学习路径。",
        "为每个进阶知识点设计一个衔接练习。",
    ],
    confidence_with_docs="medium",
)

from app.skills.skill_agent import RetrievalStrategy, SkillAgent  # noqa: E402

agent = SkillAgent(config)
