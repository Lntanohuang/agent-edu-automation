"""课程大纲提取技能配置。"""

from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator

from app.skills.skill_config import SkillConfig


class ChapterItem(BaseModel):
    """章节条目。"""
    chapter_name: str = Field(description="章节名称")
    key_concepts: List[str] = Field(default_factory=list, description="该章核心概念")


class CurriculumOutlineOutput(BaseModel):
    """课程大纲提取的结构化输出。"""

    course_summary: str = Field(default="", description="课程整体概要（2-3句）")
    topics: List[str] = Field(default_factory=list, description="核心知识点列表")
    chapter_structure: List[ChapterItem] = Field(default_factory=list, description="章节结构")
    key_concepts: List[str] = Field(default_factory=list, description="全课程关键概念")
    prerequisites: List[str] = Field(default_factory=list, description="先修知识要求")
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

    @field_validator("chapter_structure", mode="before")
    @classmethod
    def coerce_chapter_items(cls, v):
        if isinstance(v, list):
            return [
                {"chapter_name": item, "key_concepts": []} if isinstance(item, str) else item
                for item in v
            ]
        return v


def _format(parsed: CurriculumOutlineOutput) -> str:
    chapters = "\n".join(
        f"  - {ch.chapter_name}：{', '.join(ch.key_concepts)}"
        for ch in parsed.chapter_structure
    ) if parsed.chapter_structure else "  未识别"
    return (
        f"课程概要：{parsed.course_summary}\n"
        f"核心知识点：{'; '.join(parsed.topics) if parsed.topics else '未提取'}\n"
        f"章节结构：\n{chapters}\n"
        f"关键概念：{'; '.join(parsed.key_concepts) if parsed.key_concepts else '无'}\n"
        f"先修要求：{'; '.join(parsed.prerequisites) if parsed.prerequisites else '无'}"
    )


config = SkillConfig(
    name="curriculum_outline",
    description="课程大纲提取：从教材资料中提取知识点框架、章节结构、教学重点和先修要求",
    output_schema=CurriculumOutlineOutput,
    system_prompt=(
        "你是课程设计专家。请从给定教材片段中提取课程大纲结构。"
        "包括：核心知识点、章节组织、关键概念和先修知识。"
        "只基于给定资料提取，不要编造内容。"
        "输出必须是扁平 JSON，顶层字段为：course_summary, topics, chapter_structure, key_concepts, prerequisites, exploration_tasks。不要嵌套在其他对象中。"
    ),
    format_answer=_format,
    default_tasks=[
        "对照教材目录验证提取的章节结构是否完整。",
        "标注哪些知识点需要跨章节整合教学。",
    ],
    confidence_with_docs="high",
)

from app.skills.skill_agent import RetrievalStrategy, SkillAgent  # noqa: E402

agent = SkillAgent(config)
