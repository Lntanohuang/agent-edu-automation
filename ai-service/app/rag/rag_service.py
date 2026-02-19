import logging
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.loader import load_document


logger = logging.getLogger(__name__)


def build_and_store_chunks(
    file_path: str,
    vector_store: Any,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    book_label: str | None = None,
    source_file_name: str | None = None,
) -> Dict[str, Any]:
    """
    加载文档 -> 切分 -> 写入向量库
    返回结构化结果，便于上层处理。
    """
    # 1) 参数校验
    if not file_path or not file_path.strip():
        raise ValueError("file_path 不能为空")
    if vector_store is None:
        raise ValueError("vector_store 不能为空")
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    source_name = (source_file_name or Path(file_path).name).strip()
    normalized_label = (book_label or Path(source_name).stem).strip()
    if not normalized_label:
        normalized_label = "未命名资料"
    book_id = f"book_{sha1(normalized_label.encode('utf-8')).hexdigest()[:12]}"

    logger.info(
        "Start RAG chunking: file_path=%s, chunk_size=%d, chunk_overlap=%d",
        file_path,
        chunk_size,
        chunk_overlap,
    )

    try:
        docs = load_document(file_path)
        doc_count = len(docs)
        logger.info("Loaded documents: count=%d", doc_count)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        all_splits = text_splitter.split_documents(docs)
        chunk_count = len(all_splits)
        logger.info("Split documents finished: chunks=%d", chunk_count)

        for index, doc in enumerate(all_splits):
            metadata = dict(doc.metadata or {})
            metadata["book_label"] = normalized_label
            metadata["book_id"] = book_id
            metadata["file_name"] = source_name
            metadata["chunk_index"] = index
            doc.metadata = metadata

        vector_store.add_documents(all_splits)
        logger.info("Stored chunks into vector store: chunks=%d", chunk_count)

        return {
            "success": True,
            "file_path": file_path,
            "doc_count": doc_count,
            "chunk_count": chunk_count,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "book_label": normalized_label,
            "book_id": book_id,
            "error": None,
        }

    except Exception as exc:
        logger.exception("Failed to build/store chunks: file_path=%s", file_path)
        return {
            "success": False,
            "file_path": file_path,
            "doc_count": 0,
            "chunk_count": 0,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "book_label": normalized_label,
            "book_id": book_id,
            "error": str(exc),
        }
