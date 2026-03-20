"""
智能出题路由。
"""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.question_generation_service import (
    DifficultyDistribution,
    QuestionGenerateInput,
    QuestionGenerationService,
)

router = APIRouter()
logger = get_logger(__name__)
question_generation_service = QuestionGenerationService()


class QuestionGenerateRequest(BaseModel):
    subject: str = Field(default="大学计算机", description="学科")
    topic: str = Field(default="教材重点章节", description="主题")
    textbook_scope: list[str] = Field(default_factory=list, description="教材标签过滤")
    question_count: int = Field(default=10, ge=1, le=50, description="题目数量")
    question_types: list[str] = Field(
        default_factory=lambda: ["单选题", "多选题", "判断题", "填空题", "简答题", "编程题"],
        description="题型列表",
    )
    difficulty_distribution: DifficultyDistribution = Field(default_factory=DifficultyDistribution)
    output_mode: Literal["practice", "paper"] = Field(default="practice", description="模式")
    total_score: int = Field(default=100, ge=1, le=300, description="总分")
    include_answer: bool = Field(default=True, description="兼容字段，服务端始终强制为 True")
    include_explanation: bool = Field(default=True, description="兼容字段，服务端始终强制为 True")
    require_source_citation: bool = Field(default=True, description="兼容字段，服务端始终强制为 True")


class QuestionGenerateResponse(BaseModel):
    success: bool = True
    message: str = "生成成功"
    question_set: dict = Field(default_factory=dict)
    book_labels: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
    error: str | None = None


@router.post("/generate", response_model=QuestionGenerateResponse)
async def generate_questions(request: QuestionGenerateRequest):
    """
    基于教材知识库生成题目（默认大学计算机场景）。
    """
    try:
        result = await question_generation_service.generate(
            QuestionGenerateInput(
                subject=request.subject,
                topic=request.topic,
                textbook_scope=request.textbook_scope,
                question_count=request.question_count,
                question_types=request.question_types,
                difficulty_distribution=request.difficulty_distribution,
                output_mode=request.output_mode,
                total_score=request.total_score,
                include_answer=True,
                include_explanation=True,
                require_source_citation=True,
            )
        )
        return QuestionGenerateResponse(
            success=True,
            message="生成成功",
            question_set=result.question_set.model_dump(),
            book_labels=result.book_labels,
            sources=result.sources,
            validation_notes=result.validation_notes,
            error=None,
        )
    except Exception as exc:
        logger.error("Question generation failed", error=str(exc))
        return QuestionGenerateResponse(
            success=False,
            message=f"生成失败: {str(exc)}",
            question_set={},
            book_labels=[],
            sources=[],
            validation_notes=[],
            error=str(exc),
        )
