"""Skills 统一输出数据结构。"""

from typing import List

from pydantic import BaseModel, Field


class SkillResponse(BaseModel):
    """技能执行后返回给编排层的标准结果。"""

    skill_used: str = Field(description="Selected skill name")
    answer: str = Field(description="Final answer text")
    sources: List[str] = Field(default_factory=list, description="Evidence sources")
    book_labels: List[str] = Field(default_factory=list, description="Matched book labels")
    exploration_tasks: List[str] = Field(default_factory=list, description="Suggested exploration tasks")
    confidence: str = Field(default="medium", description="Confidence level")
