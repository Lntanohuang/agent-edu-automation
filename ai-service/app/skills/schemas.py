from typing import List

from pydantic import BaseModel, Field


class SkillResponse(BaseModel):
    skill_used: str = Field(description="Selected skill name")
    answer: str = Field(description="Final answer text")
    sources: List[str] = Field(default_factory=list, description="Evidence sources")
    book_labels: List[str] = Field(default_factory=list, description="Matched book labels")
    exploration_tasks: List[str] = Field(default_factory=list, description="Suggested exploration tasks")
    confidence: str = Field(default="medium", description="Confidence level")
