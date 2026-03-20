import os
from functools import lru_cache

from langchain_chroma import Chroma

from app.core.config import settings
from app.llm.model_factory import ollama_embedding_model


@lru_cache(maxsize=1)
def get_rag_vector_store() -> Chroma:
    """
    初始化并返回 RAG 使用的 Chroma 向量库（单例）。
    """
    os.makedirs(settings.chroma_persist_directory, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=ollama_embedding_model,
        persist_directory=settings.chroma_persist_directory,
    )
