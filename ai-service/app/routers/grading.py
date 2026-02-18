"""
作业批阅路由

测试 JSON:

1. 作文批阅:
{
    "content": "春天来了，小草绿了...",
    "title": "我的春天",
    "rubric": [
        {"criteria": "内容完整性", "weight": 30, "description": "内容充实"},
        {"criteria": "语言表达", "weight": 30, "description": "语言流畅"},
        {"criteria": "结构", "weight": 20, "description": "结构清晰"},
        {"criteria": "创新性", "weight": 20, "description": "有创意"}
    ],
    "grade": "高一"
}

2. 代码批阅:
{
    "code": "def fib(n):\n    if n <= 1:\n        return n\n    return fib(n-1) + fib(n-2)",
    "language": "python",
    "problem": "实现斐波那契数列"
}

3. 批量批阅:
{
    "type": "essay",
    "submissions": [
        {"id": "sub_001", "content": "作文1..."},
        {"id": "sub_002", "content": "作文2..."}
    ]
}
"""
from fastapi import APIRouter

from app.core.logging import get_logger
from app.models.schemas import (
    CodeGradingRequest,
    CodeGradingResponse,
    EssayGradingRequest,
    EssayGradingResponse,
    GradingType,
)
from app.services.grading_service import GradingService

router = APIRouter()
logger = get_logger(__name__)

grading_service = GradingService()


@router.post("/essay", response_model=EssayGradingResponse)
async def grade_essay(request: EssayGradingRequest):
    """
    作文批阅
    
    支持：
    - 自动评分
    - 错别字检查
    - 优缺点分析
    - 改进建议
    """
    try:
        result = await grading_service.grade_essay(request)
        return EssayGradingResponse(
            **result,
            message="批阅完成",
        )
    except Exception as e:
        logger.error("Essay grading failed", error=str(e))
        return EssayGradingResponse(
            success=False,
            message=f"批阅失败: {str(e)}",
            overall_score=0,
            overall_comment="",
            strengths=[],
            weaknesses=[],
            suggestions=[],
            criteria_scores=[],
            detailed_comments="",
        )


@router.post("/code", response_model=CodeGradingResponse)
async def grade_code(request: CodeGradingRequest):
    """
    代码批阅
    
    支持：
    - 语法检查
    - 测试用例运行
    - 代码质量评估
    - 优化建议
    """
    try:
        result = await grading_service.grade_code(request)
        return CodeGradingResponse(
            **result,
            message="批阅完成",
        )
    except Exception as e:
        logger.error("Code grading failed", error=str(e))
        return CodeGradingResponse(
            success=False,
            message=f"批阅失败: {str(e)}",
            score=0,
            code_quality={},
            suggestions=[],
        )


@router.post("/math")
async def grade_math(request: dict):
    """
    数学解答批阅
    
    检查解题步骤和最终答案
    """
    try:
        result = await grading_service.grade_math(request)
        return {
            "success": True,
            **result,
        }
    except Exception as e:
        logger.error("Math grading failed", error=str(e))
        return {
            "success": False,
            "message": f"批阅失败: {str(e)}",
        }


@router.post("/english-essay")
async def grade_english_essay(request: dict):
    """
    英语作文批阅
    
    支持：
    - 语法检查
    - 词汇建议
    - 句式改进
    """
    try:
        result = await grading_service.grade_english_essay(request)
        return {
            "success": True,
            **result,
        }
    except Exception as e:
        logger.error("English essay grading failed", error=str(e))
        return {
            "success": False,
            "message": f"批阅失败: {str(e)}",
        }


@router.post("/batch")
async def batch_grade(request: dict):
    """
    批量批阅
    
    适用于大规模作业批改，返回批阅任务ID
    """
    try:
        result = await grading_service.batch_grade(request)
        return {
            "success": True,
            "batch_id": result["batch_id"],
            "status": "processing",
            "estimated_time": result.get("estimated_time", 0),
        }
    except Exception as e:
        logger.error("Batch grading failed", error=str(e))
        return {
            "success": False,
            "message": f"批量批阅失败: {str(e)}",
        }


@router.get("/batch/{batch_id}/progress")
async def get_batch_progress(batch_id: str):
    """
    查询批量批阅进度
    """
    try:
        progress = await grading_service.get_batch_progress(batch_id)
        return {
            "success": True,
            **progress,
        }
    except Exception as e:
        logger.error("Get batch progress failed", error=str(e))
        return {
            "success": False,
            "message": f"查询失败: {str(e)}",
        }
