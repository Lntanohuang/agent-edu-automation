from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.config import settings


# 向量模型（供 Chroma embedding_function 使用）
ollama_embedding_model = OllamaEmbeddings(
    model=settings.ollama_embedding_model,
    base_url=settings.ollama_base_url,
)

# Qwen 聊天模型（可通过 .env 的 ollama_qwen_* 配置覆盖）
ollama_qwen_llm = ChatOllama(
    model=settings.ollama_qwen_model,
    base_url=settings.ollama_qwen_url or settings.ollama_base_url,
    temperature=settings.openai_temperature,
)
