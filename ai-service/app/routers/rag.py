"""
RAG 路由
"""
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, File, Form, Request, UploadFile
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.core.logging import get_logger
from app.llm.vector_store import get_rag_vector_store
from app.rag.rag_service import build_and_store_chunks
from app.services.rag_chat_service import RagChatService

router = APIRouter()
logger = get_logger(__name__)
rag_chat_service = RagChatService()


class RagIndexRequest(BaseModel):
    file_path: str = Field(..., description="待索引文件的本地路径")
    chunk_size: int = Field(default=1000, gt=0, description="分块大小")
    chunk_overlap: int = Field(default=200, ge=0, description="分块重叠")
    book_label: str | None = Field(default=None, description="书本标签（不传则按文件名自动生成）")


class RagIndexResponse(BaseModel):
    success: bool = True
    message: str = "索引完成"
    file_path: str
    doc_count: int = 0
    chunk_count: int = 0
    chunk_size: int
    chunk_overlap: int
    book_label: str | None = None
    book_id: str | None = None
    error: str | None = None


class ChatHistoryMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    tool_call_id: str | None = Field(default=None, description="tool 消息关联 id")


class RagAgentChatRequest(BaseModel):
    query: str = Field(..., description="用户问题")
    conversation_id: str | None = Field(default=None, description="会话 ID（同一会话保持一致）")
    history: list[ChatHistoryMessage] = Field(default_factory=list, description="历史消息")
    max_history_tokens: int = Field(default=512, ge=64, le=4096, description="历史裁剪 token 上限")
    trace_project_name: str | None = Field(default=None, description="可选：覆盖 LangSmith project 名称")


class RagAgentChatResponse(BaseModel):
    success: bool = True
    message: str = "调用成功"
    answer: str = ""
    skill_used: str | None = Field(default=None, description="命中的技能名称")
    sources: list[str] = Field(default_factory=list, description="依据来源")
    exploration_tasks: list[str] = Field(default_factory=list, description="探索任务")
    book_labels: list[str] = Field(default_factory=list, description="命中的书本标签")
    confidence: str = Field(default="medium", description="回答可信度")
    audit_notes: list[str] = Field(default_factory=list, description="来源审核备注")
    error: str | None = None


class RagBookItem(BaseModel):
    book_id: str = Field(..., description="书本唯一 ID")
    book_label: str = Field(..., description="书本标签")
    file_name: str | None = Field(default=None, description="来源文件名")
    chunk_count: int = Field(default=0, description="已索引分块数")


class RagBookListResponse(BaseModel):
    success: bool = True
    message: str = "查询成功"
    total: int = 0
    items: list[RagBookItem] = Field(default_factory=list)
    error: str | None = None


def _to_langchain_message(item: ChatHistoryMessage) -> BaseMessage:
    if item.role == "system":
        return SystemMessage(content=item.content)
    if item.role == "assistant":
        return AIMessage(content=item.content)
    if item.role == "tool":
        return ToolMessage(content=item.content, tool_call_id=item.tool_call_id or "tool-call")
    return HumanMessage(content=item.content)


def _flatten_metadatas(raw_metadatas):
    if not isinstance(raw_metadatas, list):
        return []
    flattened: list[dict] = []
    for item in raw_metadatas:
        if isinstance(item, dict):
            flattened.append(item)
        elif isinstance(item, list):
            for sub in item:
                if isinstance(sub, dict):
                    flattened.append(sub)
    return flattened


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
            book_label=request.book_label,
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
            book_label=result.get("book_label"),
            book_id=result.get("book_id"),
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
            book_label=request.book_label,
            book_id=None,
            error=str(exc),
        )


@router.post("/index-by-file", response_model=RagIndexResponse)
async def index_by_file(
    file: UploadFile = File(..., description="待索引文件（支持 .pdf/.txt/.docx）"),
    chunk_size: int = Form(default=1000, gt=0, description="分块大小"),
    chunk_overlap: int = Form(default=200, ge=0, description="分块重叠"),
    book_label: str | None = Form(default=None, description="书本标签（不传则按文件名自动生成）"),
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
            book_label=book_label,
            source_file_name=file.filename or Path(tmp_path).name,
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
            book_label=result.get("book_label"),
            book_id=result.get("book_id"),
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
            book_label=book_label,
            book_id=None,
            error=str(exc),
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning("Failed to remove temp file", temp_path=tmp_path)


@router.post("/agent/chat", response_model=RagAgentChatResponse)
async def rag_agent_chat(payload: RagAgentChatRequest, raw_request: Request):
    """
    基于 RAG + Skill Router 的对话
    """
    trace_id = raw_request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
    started_at = time.time()
    logger.info(
        "rag_agent_chat_received",
        trace_id=trace_id,
        conversation_id=payload.conversation_id,
        history_count=len(payload.history),
        max_history_tokens=payload.max_history_tokens,
        query_chars=len(payload.query),
    )
    try:
        history_messages = [_to_langchain_message(item) for item in payload.history]
        langsmith_extra = {"project_name": payload.trace_project_name} if payload.trace_project_name else None
        result = await rag_chat_service.chat(
            query=payload.query,
            history_messages=history_messages,
            conversation_id=payload.conversation_id,
            max_history_tokens=payload.max_history_tokens,
            langsmith_extra=langsmith_extra,
            trace_id=trace_id,
        )
        logger.info(
            "rag_agent_chat_succeeded",
            trace_id=trace_id,
            conversation_id=payload.conversation_id,
            elapsed_ms=round((time.time() - started_at) * 1000, 1),
            skill_used=result.get("skill_used"),
            confidence=result.get("confidence"),
            source_count=len(result.get("sources", [])),
            exploration_task_count=len(result.get("exploration_tasks", [])),
            book_label_count=len(result.get("book_labels", [])),
        )
        return RagAgentChatResponse(
            success=True,
            message="调用成功",
            answer=result["answer"],
            skill_used=result["skill_used"],
            sources=result["sources"],
            exploration_tasks=result["exploration_tasks"],
            book_labels=result["book_labels"],
            confidence=result["confidence"],
            audit_notes=result["audit_notes"],
            error=None,
        )
    except Exception as exc:
        logger.error(
            "rag_agent_chat_failed",
            trace_id=trace_id,
            conversation_id=payload.conversation_id,
            elapsed_ms=round((time.time() - started_at) * 1000, 1),
            error=str(exc),
        )
        return RagAgentChatResponse(
            success=False,
            message=f"调用失败: {str(exc)}",
            answer="",
            skill_used=None,
            sources=[],
            exploration_tasks=[],
            book_labels=[],
            confidence="low",
            audit_notes=[],
            error=str(exc),
        )


@router.get("/books", response_model=RagBookListResponse)
async def list_rag_books():
    """
    列出当前 RAG 向量库中的所有书本（按 book_id/book_label 聚合）
    """
    try:
        vector_store = get_rag_vector_store()
        records = vector_store.get(include=["metadatas"])
        metadatas = _flatten_metadatas(records.get("metadatas"))

        aggregate: dict[str, dict] = {}
        for metadata in metadatas:
            label = str(
                metadata.get("book_label")
                or metadata.get("file_name")
                or metadata.get("source")
                or "未知资料"
            ).strip()
            book_id = str(metadata.get("book_id") or f"legacy_{label}").strip()
            file_name = str(metadata.get("file_name") or "").strip() or None
            key = f"{book_id}::{label}"
            if key not in aggregate:
                aggregate[key] = {
                    "book_id": book_id,
                    "book_label": label,
                    "file_name": file_name,
                    "chunk_count": 0,
                }
            aggregate[key]["chunk_count"] += 1
            if not aggregate[key]["file_name"] and file_name:
                aggregate[key]["file_name"] = file_name

        items = [
            RagBookItem(
                book_id=value["book_id"],
                book_label=value["book_label"],
                file_name=value["file_name"],
                chunk_count=value["chunk_count"],
            )
            for value in aggregate.values()
        ]
        items.sort(key=lambda item: (-item.chunk_count, item.book_label))
        return RagBookListResponse(
            success=True,
            message="查询成功",
            total=len(items),
            items=items,
            error=None,
        )
    except Exception as exc:
        logger.error("List RAG books failed", error=str(exc))
        return RagBookListResponse(
            success=False,
            message=f"查询失败: {str(exc)}",
            total=0,
            items=[],
            error=str(exc),
        )
