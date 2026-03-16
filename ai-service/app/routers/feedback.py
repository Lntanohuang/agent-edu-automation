"""
用户反馈端点：收集用户对 RAG 回答的评价，存入 MongoDB。
"""

import time
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """用户反馈请求。"""

    conversation_id: str
    message_id: str
    rating: Literal["helpful", "not_helpful"]
    comment: Optional[str] = None
    confidence: Optional[str] = None


class FeedbackResponse(BaseModel):
    """反馈提交响应。"""

    success: bool
    message: str


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    提交用户反馈。

    存入 MongoDB ai_service.feedback collection。
    """
    try:
        from pymongo import MongoClient

        client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
        db = client[settings.mongodb_database]
        collection = db["feedback"]
        collection.insert_one({
            "conversation_id": request.conversation_id,
            "message_id": request.message_id,
            "rating": request.rating,
            "comment": request.comment,
            "confidence": request.confidence,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        logger.info(
            "用户反馈已保存",
            conversation_id=request.conversation_id,
            rating=request.rating,
        )
        return FeedbackResponse(success=True, message="反馈已提交")
    except Exception as exc:
        logger.warning("保存用户反馈失败", error=str(exc))
        return FeedbackResponse(success=False, message=f"保存失败: {str(exc)}")
