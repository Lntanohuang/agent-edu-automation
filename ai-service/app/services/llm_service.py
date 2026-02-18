"""
LLM 服务封装
"""
import json
from typing import AsyncGenerator, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import ChatCompletionRequest, EducationChatRequest

logger = get_logger(__name__)


class LLMService:
    """LLM 服务类"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        
        # 教育领域系统提示词
        self.education_system_prompt = """你是一位经验丰富的教育专家，拥有深厚的教学理论知识和丰富的课堂实践经验。

你的专长包括：
1. 教学设计与课程规划
2. 课堂管理与学生互动
3. 教学评估与反馈
4. 教育心理学应用
5. 创新教学方法

回答时请：
- 专业、准确、实用
- 提供具体的操作步骤和案例
- 考虑不同年级和学科的特点
- 使用教育领域的专业术语
- 给出可落地的建议"""

    async def chat_completion(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        """通用对话完成"""
        try:
            # 转换消息格式
            messages = []
            for msg in request.messages:
                if msg.role == "system":
                    messages.append(SystemMessage(content=msg.content))
                elif msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
            
            # 调用 LLM
            response = await self.llm.ainvoke(messages)
            
            return {
                "content": response.content,
                "usage": {
                    "prompt_tokens": response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": response.response_metadata.get("token_usage", {}).get("completion_tokens", 0),
                    "total_tokens": response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
                }
            }
        except Exception as e:
            logger.error("Chat completion error", error=str(e))
            raise

    async def stream_chat_completion(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """流式对话完成"""
        try:
            messages = []
            for msg in request.messages:
                if msg.role == "system":
                    messages.append(SystemMessage(content=msg.content))
                elif msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
            
            # 流式调用
            async for chunk in self.llm.astream(messages):
                data = json.dumps({"content": chunk.content, "done": False})
                yield f"data: {data}\n\n"
            
            # 结束标记
            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            
        except Exception as e:
            logger.error("Stream chat completion error", error=str(e))
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    async def education_chat(self, request: EducationChatRequest) -> Dict[str, Any]:
        """教育领域专用问答"""
        try:
            # 构建提示词
            context_info = ""
            if request.context:
                subject = request.context.get("subject", "")
                grade = request.context.get("grade", "")
                if subject or grade:
                    context_info = f"（针对{grade}{subject}教学）"
            
            messages = [
                SystemMessage(content=self.education_system_prompt),
                HumanMessage(content=f"{request.query}{context_info}")
            ]
            
            # 调用 LLM
            response = await self.llm.ainvoke(messages)
            
            # 生成建议追问（简单实现，可优化）
            suggested_questions = await self._generate_suggested_questions(request.query)
            
            return {
                "answer": response.content,
                "sources": None,  # TODO: 集成 RAG
                "suggested_questions": suggested_questions,
            }
        except Exception as e:
            logger.error("Education chat error", error=str(e))
            raise


    async def _generate_suggested_questions(self, query: str) -> list:
        """生成建议追问"""
        # TODO 用structured output控制输出格式
        try:
            prompt = f"基于用户问题'{query}'，生成3个相关的追问问题，用JSON数组格式返回。"
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            # 尝试解析 JSON
            try:
                questions = json.loads(response.content)
                if isinstance(questions, list):
                    return questions[:3]
            except:
                pass
            
            return [
                "能否详细说明一下？",
                "有哪些具体的实施方法？",
                "如何评估效果？",
            ]
        except:
            return []
