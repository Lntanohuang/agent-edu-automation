"""
知识库路由 (RAG)

测试 JSON:

1. 文档上传后搜索:
{
    "query": "一元二次方程的解法",
    "filters": {
        "subject": "数学",
        "grade": "初二"
    },
    "top_k": 5
}

2. 仅上传文档 (Multipart):
POST /knowledge/upload
- file: document.pdf
- metadata: {"subject": "数学", "type": "教案"}
"""
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field
from typing import Optional

from app.core.logging import get_logger
from app.models.schemas import (
    DocumentUploadResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter()
logger = get_logger(__name__)

knowledge_service = KnowledgeService()


class ConfirmDraftRequest(BaseModel):
    draft_id: str = Field(..., description="草稿ID")
    approved: bool = Field(default=True, description="是否确认入库")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="上传的文件"),
    metadata: Optional[str] = Form(None, description="JSON格式的元数据"),
):
    """
    上传文档到知识库
    
    支持的格式：PDF, Word, TXT, Markdown
    
    流程：
    1. 文件上传
    2. 转换为 Markdown
    3. 人工确认
    4. 确认后向量化存储
    """
    try:
        import json
        meta_dict = {}
        if metadata is not None:
            meta_str = metadata.strip()
            if meta_str:
                try:
                    meta_dict = json.loads(meta_str)
                except json.JSONDecodeError:
                    return DocumentUploadResponse(
                        success=False,
                        message="metadata 必须是有效的 JSON 字符串",
                        document_id="",
                        chunks=0,
                        status="failed",
                    )
        
        result = await knowledge_service.upload_document(file, meta_dict)
        return DocumentUploadResponse(
            document_id=result["document_id"],
            chunks=result["chunks"],
            status=result["status"],
            draft_id=result["draft_id"],
            markdown_preview=result["markdown_preview"],
            message="文档已转换为 Markdown，请确认后入库",
        )
    except Exception as e:
        logger.error("Document upload failed", error=str(e))
        return DocumentUploadResponse(
            success=False,
            message=f"上传失败: {str(e)}",
            document_id="",
            chunks=0,
            status="failed",
        )


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """
    获取待确认的 Markdown 草稿
    """
    try:
        return {
            "success": True,
            "draft": knowledge_service.get_draft(draft_id),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "草稿不存在或已处理",
        }
    except Exception as e:
        logger.error("Get draft failed", error=str(e), draft_id=draft_id)
        return {
            "success": False,
            "message": f"获取草稿失败: {str(e)}",
        }


@router.post("/confirm", response_model=DocumentUploadResponse)
async def confirm_upload(request: ConfirmDraftRequest):
    """
    确认草稿并入库
    """
    try:
        result = knowledge_service.confirm_document(
            draft_id=request.draft_id,
            approved=request.approved,
        )
        if result["status"] == "indexed":
            message = "文档已确认并写入向量库"
        else:
            message = "文档已驳回，未写入向量库"
        return DocumentUploadResponse(
            document_id=result["document_id"],
            chunks=result["chunks"],
            status=result["status"],
            draft_id=result["draft_id"],
            markdown_preview=result["markdown_preview"],
            message=message,
        )
    except FileNotFoundError:
        return DocumentUploadResponse(
            success=False,
            message="草稿不存在或已处理",
            document_id="",
            chunks=0,
            status="failed",
        )
    except Exception as e:
        logger.error("Confirm draft failed", error=str(e), draft_id=request.draft_id)
        return DocumentUploadResponse(
            success=False,
            message=f"确认失败: {str(e)}",
            document_id="",
            chunks=0,
            status="failed",
        )


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    语义搜索知识库
    
    使用向量相似度搜索相关文档片段
    """
    try:
        results = await knowledge_service.search(request)
        return KnowledgeSearchResponse(
            results=results,
            message=f"找到 {len(results)} 条结果",
        )
    except Exception as e:
        logger.error("Knowledge search failed", error=str(e))
        return KnowledgeSearchResponse(
            success=False,
            message=f"搜索失败: {str(e)}",
            results=[],
        )


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    删除知识库文档
    """
    try:
        await knowledge_service.delete_document(document_id)
        return {
            "success": True,
            "message": "文档删除成功",
        }
    except Exception as e:
        logger.error("Document deletion failed", error=str(e))
        return {
            "success": False,
            "message": f"删除失败: {str(e)}",
        }


@router.get("/documents")
async def list_documents(
    subject: Optional[str] = None,
    page: int = 1,
    size: int = 20,
):
    """
    列出知识库文档
    """
    try:
        documents = await knowledge_service.list_documents(subject, page, size)
        return {
            "success": True,
            "documents": documents,
            "page": page,
            "size": size,
        }
    except Exception as e:
        logger.error("List documents failed", error=str(e))
        return {
            "success": False,
            "message": f"查询失败: {str(e)}",
        }
