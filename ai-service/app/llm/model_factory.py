from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.config import settings


def _normalize_ollama_base_url(url: str | None) -> str:
    """Normalize Ollama base URL for langchain-ollama (expects ...:11434, not .../v1)."""
    if not url:
        return "http://127.0.0.1:11434"
    normalized = url.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    return normalized


OLLAMA_BASE_URL = _normalize_ollama_base_url(settings.ollama_base_url)
OLLAMA_QWEN_URL = _normalize_ollama_base_url(settings.ollama_qwen_url) if settings.ollama_qwen_url else OLLAMA_BASE_URL


# 向量模型（供 Chroma embedding_function 使用）
ollama_embedding_model = OllamaEmbeddings(
    model=settings.ollama_embedding_model,
    base_url=OLLAMA_BASE_URL,
)


# Qwen 聊天模型（可通过 .env 的 ollama_qwen_* 配置覆盖）
ollama_qwen_llm = ChatOllama(
    model=settings.ollama_qwen_model,
    base_url=OLLAMA_QWEN_URL,
    temperature=settings.openai_temperature,
)
