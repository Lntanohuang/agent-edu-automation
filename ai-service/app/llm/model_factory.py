from typing import Any

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

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

# trust_env=False 让 httpx 忽略系统代理
_NO_PROXY_KWARGS = {"trust_env": False}


# ── Embedding 模型 ──────────────────────────────────────────

# Ollama 本地 Embedding（降级方案）
ollama_embedding = OllamaEmbeddings(
    model=settings.ollama_embedding_model,
    base_url=OLLAMA_BASE_URL,
    client_kwargs=_NO_PROXY_KWARGS,
)

# 通义千问 Dashscope Embedding（通过 OpenAI 兼容接口）
dashscope_embedding = OpenAIEmbeddings(
    model=settings.dashscope_embedding_model,
    openai_api_key=settings.openai_api_key,
    openai_api_base=settings.openai_base_url,
)


def get_embedding_model() -> Any:
    """Return the configured embedding model."""
    provider = settings.embedding_provider.strip().lower()
    if provider == "ollama":
        return ollama_embedding
    return dashscope_embedding


embedding_model = get_embedding_model()

# Backward-compatible alias
ollama_embedding_model = embedding_model


# ── Chat 模型 ────────────────────────────────────────────────

# Ollama 本地聊天模型（降级方案）
ollama_native_qwen_llm = ChatOllama(
    model=settings.ollama_qwen_model,
    base_url=OLLAMA_QWEN_URL,
    temperature=settings.openai_temperature,
    client_kwargs=_NO_PROXY_KWARGS,
)

# MLX 本地模型（按需启用）
mlx_qwen_llm = MLXChatModel(model_path=settings.mlx_model_path or "", max_tokens=settings.mlx_max_tokens)

# 通义千问 Dashscope 聊天模型（通过 OpenAI 兼容接口）
openai_compatible_llm = ChatOpenAI(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    temperature=settings.openai_temperature,
    max_tokens=settings.openai_max_tokens,
    max_retries=2,
)


def get_chat_model() -> Any:
    """Return the configured chat model provider."""
    provider = settings.chat_provider.strip().lower()
    if provider == "mlx":
        return mlx_qwen_llm
    if provider in {"openai", "qwen_api"}:
        return openai_compatible_llm
    return ollama_native_qwen_llm


chat_llm = get_chat_model()

# Backward-compatible alias for existing imports.
ollama_qwen_llm = chat_llm
