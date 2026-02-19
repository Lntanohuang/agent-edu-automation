"""
Pydantic 数据模型
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 通用模型 ====================

class ResponseBase(BaseModel):
    """通用响应基类"""
    success: bool = Field(default=True, description="是否成功")
    message: Optional[str] = Field(default=None, description="消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")


# ==================== 知识库模型 ====================

class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    metadata: Optional[Dict[str, str]] = Field(default=None, description="元数据")


class DocumentUploadResponse(ResponseBase):
    """文档上传响应"""
    document_id: str = Field(..., description="文档ID")
    chunks: int = Field(..., description="切分成的文本块数")
    status: str = Field(..., description="状态")
    draft_id: Optional[str] = Field(default=None, description="待确认草稿ID")
    markdown_preview: Optional[str] = Field(default=None, description="Markdown预览")


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求"""
    query: str = Field(..., description="搜索查询")
    filters: Optional[Dict[str, str]] = Field(default=None, description="过滤条件")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数")


class KnowledgeSearchResponse(ResponseBase):
    """知识库搜索响应"""
    results: List[Dict[str, Any]] = Field(..., description="搜索结果")
