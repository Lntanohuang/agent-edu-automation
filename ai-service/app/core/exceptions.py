"""
自定义异常体系。

所有 AI 服务内部异常均继承 EduPlatformError，
便于 FastAPI 全局 exception_handler 统一捕获并返回结构化响应。
"""

from __future__ import annotations


class EduPlatformError(Exception):
    """基础业务异常。"""

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class LLMError(EduPlatformError):
    """LLM 调用失败（超时、返回空、解析失败等）。"""


class RetrievalError(EduPlatformError):
    """检索链路失败（ChromaDB / BM25 / Rerank）。"""


class SkillError(EduPlatformError):
    """Skill 执行失败。"""


class ValidationError(EduPlatformError):
    """检索验证 / 质量评估失败。"""


class DocumentIngestionError(EduPlatformError):
    """文档导入 / 索引失败。"""
