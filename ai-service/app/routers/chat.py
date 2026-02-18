"""
智能问答路由

测试 JSON:

1. 普通对话:
{
    "messages": [
        {"role": "system", "content": "你是一位经验丰富的数学教师"},
        {"role": "user", "content": "如何设计一堂生动有趣的数学课？"}
    ],
    "model": "gpt-4",
    "temperature": 0.7,
    "stream": false
}

2. 教育领域问答 (带 RAG):
{
    "query": "如何在课堂中融入德育教育？",
    "context": {
        "subject": "语文",
        "grade": "初中"
    },
    "use_knowledge_base": true
}

3. 流式对话 (SSE):
{
    "messages": [
        {"role": "user", "content": "讲个笑话"}
    ],
    "stream": true
}
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EducationChatRequest,
    EducationChatResponse,
)
from app.services.llm_service import LLMService

router = APIRouter()
logger = get_logger(__name__)

# 初始化 LLM 服务
llm_service = LLMService()


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest):
    """
    通用对话接口
    
    兼容 OpenAI API 格式，支持多轮对话
    """
    try:
        if request.stream:
            # 流式响应
            return StreamingResponse(
                llm_service.stream_chat_completion(request),
                media_type="text/event-stream",
            )
        
        # 非流式响应
        result = await llm_service.chat_completion(request)
        return ChatCompletionResponse(
            content=result["content"],
            usage=result.get("usage"),
        )
    except Exception as e:
        logger.error("Chat completion failed", error=str(e))
        return ChatCompletionResponse(
            success=False,
            message=f"对话失败: {str(e)}",
            content="",
        )


@router.post("/education", response_model=EducationChatResponse)
async def education_chat(request: EducationChatRequest):
    """
    教育领域专用问答接口
    
    特点:
    1. 内置教育领域 Prompt
    2. 可选 RAG 知识库增强
    3. 自动追问建议
    """
    try:
        result = await llm_service.education_chat(request)
        return EducationChatResponse(
            answer=result["answer"],
            sources=result.get("sources"),
            suggested_questions=result.get("suggested_questions"),
        )
    except Exception as e:
        logger.error("Education chat failed", error=str(e))
        return EducationChatResponse(
            success=False,
            message=f"问答失败: {str(e)}",
            answer="",
        )


@router.post("/stream")
async def chat_stream(request: ChatCompletionRequest):
    """
    流式对话接口 (SSE)
    
    适用于需要实时显示 AI 生成内容的场景
    """
    request.stream = True
    return StreamingResponse(
        llm_service.stream_chat_completion(request),
        media_type="text/event-stream",
    )
