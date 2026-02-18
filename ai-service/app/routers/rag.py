"""
RAG 路由
"""
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field
from fastapi import APIRouter, File, Form, UploadFile
from langchain_core.messages import HumanMessage

from app.agents import create_rag_agent
from app.core.logging import get_logger
from app.llm.vector_store import get_rag_vector_store
from app.rag.rag_service import build_and_store_chunks

router = APIRouter()
logger = get_logger(__name__)
rag_agent = create_rag_agent()


class RagIndexRequest(BaseModel):
    file_path: str = Field(..., description="待索引文件的本地路径")
    chunk_size: int = Field(default=1000, gt=0, description="分块大小")
    chunk_overlap: int = Field(default=200, ge=0, description="分块重叠")


class RagIndexResponse(BaseModel):
    success: bool = True
    message: str = "索引完成"
    file_path: str
    doc_count: int = 0
    chunk_count: int = 0
    chunk_size: int
    chunk_overlap: int
    error: str | None = None


class RagAgentChatRequest(BaseModel):
    query: str = Field(..., description="用户问题")


class RagAgentChatResponse(BaseModel):
    success: bool = True
    message: str = "调用成功"
    answer: str = ""
    error: str | None = None


@router.post("/index-by-path", response_model=RagIndexResponse)
async def index_by_path(request: RagIndexRequest):
    """
    根据本地文件路径进行 RAG 切分并写入向量库
    """
    try:
        result = build_and_store_chunks(
            file_path=request.file_path,
            vector_store=get_rag_vector_store(),
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
        message = "索引完成" if result["success"] else "索引失败"
        return RagIndexResponse(
            success=result["success"],
            message=message,
            file_path=result["file_path"],
            doc_count=result["doc_count"],
            chunk_count=result["chunk_count"],
            chunk_size=result["chunk_size"],
            chunk_overlap=result["chunk_overlap"],
            error=result["error"],
        )
    except Exception as exc:
        logger.error("RAG index by path failed", error=str(exc), file_path=request.file_path)
        return RagIndexResponse(
            success=False,
            message=f"索引失败: {str(exc)}",
            file_path=request.file_path,
            doc_count=0,
            chunk_count=0,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            error=str(exc),
        )


@router.post("/index-by-file", response_model=RagIndexResponse)
async def index_by_file(
    file: UploadFile = File(..., description="待索引文件（支持 .pdf/.txt/.docx）"),
    chunk_size: int = Form(default=1000, gt=0, description="分块大小"),
    chunk_overlap: int = Form(default=200, ge=0, description="分块重叠"),
):
    """
    上传文件并进行 RAG 切分后写入向量库
    """
    tmp_path = None
    try:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".pdf", ".txt", ".docx"}:
            return RagIndexResponse(
                success=False,
                message=f"不支持的文件类型: {suffix or '(无后缀)'}",
                file_path=file.filename or "",
                doc_count=0,
                chunk_count=0,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                error="unsupported_file_type",
            )

        file_bytes = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        result = build_and_store_chunks(
            file_path=tmp_path,
            vector_store=get_rag_vector_store(),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        message = "索引完成" if result["success"] else "索引失败"
        return RagIndexResponse(
            success=result["success"],
            message=message,
            file_path=file.filename or tmp_path,
            doc_count=result["doc_count"],
            chunk_count=result["chunk_count"],
            chunk_size=result["chunk_size"],
            chunk_overlap=result["chunk_overlap"],
            error=result["error"],
        )
    except Exception as exc:
        logger.error("RAG index by file failed", error=str(exc), filename=file.filename)
        return RagIndexResponse(
            success=False,
            message=f"索引失败: {str(exc)}",
            file_path=file.filename or "",
            doc_count=0,
            chunk_count=0,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            error=str(exc),
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning("Failed to remove temp file", temp_path=tmp_path)


@router.post("/agent/chat", response_model=RagAgentChatResponse)
async def rag_agent_chat(request: RagAgentChatRequest):
    """
    基于 RAG 检索工具的 Agent 对话
    """
    try:
        result = await rag_agent.ainvoke({"messages": [HumanMessage(content=request.query)]})
        messages = result.get("messages", []) if isinstance(result, dict) else []
        answer = messages[-1].content if messages else ""
        return RagAgentChatResponse(
            success=True,
            message="调用成功",
            answer=answer,
            error=None,
        )
    except Exception as exc:
        logger.error("RAG agent chat failed", error=str(exc))
        return RagAgentChatResponse(
            success=False,
            message=f"调用失败: {str(exc)}",
            answer="",
            error=str(exc),
        )
