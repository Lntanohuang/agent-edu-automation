from typing import Any

from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.config import settings
from app.llm.mlx_chat_model import MLXChatModel


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

# trust_env=False 让 httpx 忽略系统代理（macOS System Preferences / Clash 等），避免 Ollama 请求 503
_NO_PROXY_KWARGS = {"trust_env": False}

# 向量模型（供 Chroma embedding_function 使用）
ollama_embedding_model = OllamaEmbeddings(
    model=settings.ollama_embedding_model,
    base_url=OLLAMA_BASE_URL,
    client_kwargs=_NO_PROXY_KWARGS,
)


# 原生 Ollama 聊天模型（始终保留）
ollama_native_qwen_llm = ChatOllama(
    model=settings.ollama_qwen_model,
    base_url=OLLAMA_QWEN_URL,
    temperature=settings.openai_temperature,
    client_kwargs=_NO_PROXY_KWARGS,
)

# 原生 MLX 本地模型（按需启用）
mlx_qwen_llm = MLXChatModel(model_path=settings.mlx_model_path or "", max_tokens=settings.mlx_max_tokens)


def get_chat_model() -> Any:
    """Return the configured chat model provider."""
    provider = settings.chat_provider.strip().lower()
    if provider == "mlx":
        return mlx_qwen_llm
    return ollama_native_qwen_llm


chat_llm = get_chat_model()

# Backward-compatible alias for existing imports.
ollama_qwen_llm = chat_llm
