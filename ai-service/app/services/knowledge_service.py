"""
知识库服务 (RAG)
"""
import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.llm.model_factory import ollama_embedding_model
from app.core.logging import get_logger
from app.models.schemas import KnowledgeSearchRequest
from app.rag.frontmatter_parser import parse_frontmatter
from app.rag.legal_splitter import split_legal_document

logger = get_logger(__name__)


class KnowledgeService:
    """知识库服务"""

    SUPPORTED_EXTENSIONS = {
        ".pdf": PyPDFLoader,
        ".docx": UnstructuredWordDocumentLoader,
        ".doc": UnstructuredWordDocumentLoader,
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
    }
    
    def __init__(self):
        self.embeddings = ollama_embedding_model
        
        # 确保目录存在
        os.makedirs(settings.chroma_persist_directory, exist_ok=True)
        
        self.vectorstore = Chroma(
            collection_name=settings.chroma_collection_name,
            embedding_function=self.embeddings,
            persist_directory=settings.chroma_persist_directory,
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", "。", "；", " ", ""],
        )

        self.staging_dir = Path(settings.chroma_persist_directory) / "knowledge_drafts"
        self.staging_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_document(self, file, metadata: dict) -> dict:
        """
        上传文档（第一阶段）
        1. 解析文件
        2. 转为 Markdown
        3. 生成草稿，等待确认
        """
        file_bytes = await file.read()
        file_name = file.filename or "unnamed"
        suffix = Path(file_name).suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix or '(无后缀)'}")

        doc_id = hashlib.md5(file_bytes).hexdigest()

        documents = self._load_documents(file_bytes, suffix)
        markdown_content = self._documents_to_markdown(documents, file_name)

        draft_id = uuid.uuid4().hex
        draft_path = self._draft_path(draft_id)
        draft_data = {
            "draft_id": draft_id,
            "document_id": doc_id,
            "filename": file_name,
            "metadata": metadata,
            "markdown_content": markdown_content,
        }
        with open(draft_path, "w", encoding="utf-8") as draft_file:
            json.dump(draft_data, draft_file, ensure_ascii=False)

        logger.info(
            "Document converted to markdown and staged",
            draft_id=draft_id,
            doc_id=doc_id,
            filename=file_name,
            markdown_chars=len(markdown_content),
        )

        return {
            "document_id": doc_id,
            "chunks": 0,
            "status": "pending_confirmation",
            "draft_id": draft_id,
            "markdown_preview": markdown_content[:2000],
        }

    def get_draft(self, draft_id: str) -> dict:
        """获取待确认草稿内容"""
        draft_path = self._draft_path(draft_id)
        if not draft_path.exists():
            raise FileNotFoundError(f"草稿不存在: {draft_id}")
        with open(draft_path, "r", encoding="utf-8") as draft_file:
            return json.load(draft_file)

    def confirm_document(self, draft_id: str, approved: bool = True) -> dict:
        """
        确认草稿（第二阶段）
        approved=True 才会写入向量库
        """
        draft = self.get_draft(draft_id)
        draft_path = self._draft_path(draft_id)

        if not approved:
            draft_path.unlink(missing_ok=True)
            return {
                "document_id": draft.get("document_id", ""),
                "chunks": 0,
                "status": "rejected",
                "draft_id": draft_id,
                "markdown_preview": "",
            }

        markdown_content = draft.get("markdown_content", "")
        fm_metadata, body = parse_frontmatter(markdown_content)

        if fm_metadata.get("doc_type") in ("statute", "interpretation", "case", "contract"):
            # 法律文档：使用领域化切块
            merged_meta = {
                "doc_id": draft["document_id"],
                "filename": draft["filename"],
                **draft.get("metadata", {}),
                **fm_metadata,
            }
            docs = split_legal_document(body, merged_meta)
            chunks = [d.page_content for d in docs]
            metadatas = []
            for i, d in enumerate(docs):
                meta = {**d.metadata, "chunk_index": i}
                # ChromaDB 不支持 list 类型 metadata
                for k, v in list(meta.items()):
                    if isinstance(v, list):
                        meta[k] = ", ".join(str(x) for x in v)
                metadatas.append(meta)
        else:
            # 通用文档：使用通用切块
            chunks = self.text_splitter.split_text(markdown_content)
            metadatas = [
                {
                    "doc_id": draft["document_id"],
                    "chunk_index": index,
                    "filename": draft["filename"],
                    **draft.get("metadata", {}),
                }
                for index in range(len(chunks))
            ]

        self.vectorstore.add_texts(
            texts=chunks,
            metadatas=metadatas,
            ids=[f"{draft['document_id']}_{index}" for index in range(len(chunks))],
        )

        if hasattr(self.vectorstore, "persist"):
            self.vectorstore.persist()
        elif hasattr(self.vectorstore, "_client") and hasattr(self.vectorstore._client, "persist"):
            self.vectorstore._client.persist()

        draft_path.unlink(missing_ok=True)
        logger.info(
            "Document confirmed and indexed",
            draft_id=draft_id,
            doc_id=draft["document_id"],
            filename=draft["filename"],
            chunks=len(chunks),
        )
        return {
            "document_id": draft["document_id"],
            "chunks": len(chunks),
            "status": "indexed",
            "draft_id": draft_id,
            "markdown_preview": "",
        }

    def _load_documents(self, file_bytes: bytes, suffix: str) -> list[Document]:
        loader_class = self.SUPPORTED_EXTENSIONS[suffix]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        try:
            if loader_class is TextLoader:
                try:
                    loader = TextLoader(tmp_path, encoding="utf-8")
                    documents = loader.load()
                except Exception:
                    loader = TextLoader(tmp_path, encoding="gbk")
                    documents = loader.load()
            else:
                loader = loader_class(tmp_path)
                documents = loader.load()
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return documents

    def _documents_to_markdown(self, documents: list[Document], file_name: str) -> str:
        sections = [f"# {file_name}"]
        for index, doc in enumerate(documents, start=1):
            page_value = doc.metadata.get("page", index)
            sections.append(f"\n## Section {page_value}\n")
            sections.append(doc.page_content.strip())
        return "\n".join(sections).strip()

    def _draft_path(self, draft_id: str) -> Path:
        return self.staging_dir / f"{draft_id}.json"
    
    async def search(self, request: KnowledgeSearchRequest) -> list:
        """搜索知识库"""
        
        # 构建过滤条件
        filter_dict = request.filters if request.filters else None
        
        # 相似度搜索
        results = self.vectorstore.similarity_search_with_score(
            query=request.query,
            k=request.top_k,
            filter=filter_dict,
        )
        
        # 格式化结果
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            })
        
        return formatted_results
    
    async def delete_document(self, document_id: str):
        """删除文档"""
        # 根据 doc_id 过滤并删除
        # Chroma 的删除操作
        pass
    
    async def list_documents(self, subject: Optional[str], page: int, size: int) -> list:
        """列出文档"""
        # 简化实现
        return []
