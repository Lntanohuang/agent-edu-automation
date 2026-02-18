"""
教案生成路由

测试 JSON:

1. 生成教案:
{
    "subject": "数学",
    "grade": "初二",
    "topic": "一元二次方程",
    "duration": 2,
    "class_size": 45,
    "teaching_goals": "掌握一元二次方程的解法",
    "requirements": "需要多媒体课件，小组讨论",
    "output_format": "detailed"
}

2. 优化教案:
{
    "original_plan": { ... },
    "enhancement_type": "addActivities",
    "target": "增加更多互动环节"
}
"""
from fastapi import APIRouter

from app.core.logging import get_logger
from app.models.schemas import (
    LessonPlanGenerateRequest,
    LessonPlanResponse,
)
from app.services.lesson_plan_service import LessonPlanService

router = APIRouter()
logger = get_logger(__name__)

lesson_plan_service = LessonPlanService()


@router.post("/generate", response_model=LessonPlanResponse)
async def generate_lesson_plan(request: LessonPlanGenerateRequest):
    """
    AI 生成教案
    
    根据教学参数自动生成完整的教案，包括：
    - 教学目标（三维目标）
    - 教学重难点
    - 教学过程（详细环节）
    - 作业布置
    - 板书设计
    """
    try:
        result = await lesson_plan_service.generate(request)
        return LessonPlanResponse(
            **result,
            message="教案生成成功",
        )
    except Exception as e:
        logger.error("Lesson plan generation failed", error=str(e))
        return LessonPlanResponse(
            success=False,
            message=f"生成失败: {str(e)}",
            title="",
            subject=request.subject,
            grade=request.grade,
            duration=request.duration,
            objectives=[],
            key_points=[],
            difficulties=[],
            teaching_methods=[],
            teaching_aids=[],
            procedures=[],
            homework="",
        )


@router.post("/enhance")
async def enhance_lesson_plan(request: dict):
    """
    优化现有教案
    
    对已有教案进行智能优化，支持：
    - addActivities: 增加互动环节
    - addResources: 增加教学资源
    - simplify: 简化内容
    - differentiate: 分层教学设计
    """
    try:
        result = await lesson_plan_service.enhance(request)
        return {
            "success": True,
            "enhanced_plan": result,
            "changes": result.get("changes", []),
        }
    except Exception as e:
        logger.error("Lesson plan enhancement failed", error=str(e))
        return {
            "success": False,
            "message": f"优化失败: {str(e)}",
        }
