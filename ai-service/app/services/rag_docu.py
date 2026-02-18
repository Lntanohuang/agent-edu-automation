# 1.抓取网页
# 2.分割文件
# 3.写入向量数据库
# 4.创建agent
# 5.调用agent 检索
from pathlib import Path
from typing import List, Optional, Dict, Any

from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logging import get_logger

from langchain_core.documents import Document

logger = get_logger(__name__)

class RagService:
    """法律法规 RAG 服务"""

    # 支持的文件格式
    SUPPORTED_EXTENSIONS = {
        '.pdf': PyPDFLoader,
        '.docx': UnstructuredWordDocumentLoader,
        '.doc': UnstructuredWordDocumentLoader,
        '.txt': TextLoader,
        '.md': UnstructuredMarkdownLoader,
    }

    def __init__(self, collection_name: str = "legal_documents"):
        """
        初始化 RAG 服务

        Args:
            collection_name: ChromaDB 集合名称
        """
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        # 确保存储目录存在
        persist_dir = Path(settings.chroma_persist_directory) / collection_name
        persist_dir.mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(persist_dir),
        )

        # 文本切分器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # 每块 500 字（适合法律条文）
            chunk_overlap=100,  # 重叠 100 字（保持上下文）
            separators=["\n\n", "\n", "。", "；", " ", ""],
        )

        logger.info("RagService initialized", collection_name=collection_name)

    def _load_single_file(self, file_path: Path, base_folder: Path) -> List[Document]:
        """
        加载单个文件
        """
        ext = file_path.suffix.lower()
        loader_class = self.SUPPORTED_EXTENSIONS[ext]

        loader = loader_class(str(file_path))
        documents = loader.load()

        relative_path = file_path.relative_to(base_folder)
        for doc in documents:
            doc.metadata.update({
                "source": str(file_path),
                "file_name": file_path.name,
                "file_type": ext,
                "folder": str(relative_path.parent),
            })

        return documents

    def _store_documents(self, documents: List[Document]) -> None:
        """
        存储文档到向量数据库
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
        if hasattr(self.vectorstore, "persist"):
            self.vectorstore.persist()
        elif hasattr(self.vectorstore, "_client") and hasattr(self.vectorstore._client, "persist"):
            self.vectorstore._client.persist()

    def docu_rag(self, file_path: str) -> Dict[str, Any]:
        """
        处理单个上传文件：切分并写入 Chroma

        Args:
            file_path: 上传文件保存后的本地路径

        Returns:
            加载统计信息
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"文件不存在: {path}")

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}")

        logger.info("Loading single file", file=str(path))

        documents = self._load_single_file(path, path.parent)
        logger.info("Splitting single file", file=str(path), documents=len(documents))

        chunks = self.text_splitter.split_documents(documents)
        logger.info("Storing single file chunks", file=str(path), total_chunks=len(chunks))

        self._store_documents(chunks)

        logger.info("Stored single file chunks", file=str(path), total_chunks=len(chunks))

        return {
            "total_files": 1,
            "loaded_files": 1,
            "failed_files": 0,
            "total_chunks": len(chunks),
            "documents": [
                {
                    "file": path.name,
                    "chunks": len(chunks),
                }
            ],
        }
