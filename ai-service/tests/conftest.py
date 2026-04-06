"""
Shared fixtures for ai-service tests.

All tests run WITHOUT external dependencies (Ollama, ChromaDB, MongoDB, Redis).
LLM calls and vector store are mocked at the module level.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# ── 清除代理（必须在任何 app import 之前，避免 Ollama client 走代理导致 503） ──
for _proxy_key in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_key, None)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ── Ensure ai-service root is importable ──
AI_SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AI_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, AI_SERVICE_ROOT)

# ── Environment defaults so Settings() won't crash ──
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost/v1")
os.environ.setdefault("MONGODB_ENABLED", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")


# ── Mock LLM (used by almost every service / skill) ──

def _make_mock_llm():
    """Create a mock that mimics chat_llm interface."""
    llm = MagicMock(name="mock_chat_llm")

    structured_llm = MagicMock(name="mock_structured_llm")
    structured_llm.ainvoke = AsyncMock(return_value={})
    llm.with_structured_output.return_value = structured_llm

    llm.ainvoke = AsyncMock(return_value=MagicMock(content="mocked response"))
    return llm


@pytest.fixture()
def mock_llm():
    """Patch chat_llm globally and return the mock."""
    llm = _make_mock_llm()
    with patch("app.llm.model_factory.chat_llm", llm):
        yield llm


# ── Mock Vector Store ──

def _make_mock_vector_store():
    vs = MagicMock(name="mock_vector_store")
    vs.similarity_search.return_value = []
    vs.get.return_value = {"metadatas": []}
    vs.add_documents.return_value = None
    return vs


@pytest.fixture()
def mock_vector_store():
    vs = _make_mock_vector_store()
    with patch("app.llm.vector_store.get_rag_vector_store", return_value=vs):
        yield vs


# ── Mock Hybrid Retriever ──

@pytest.fixture()
def mock_hybrid_retriever():
    """Patch the HybridRetriever singleton for tests that use hybrid retrieval."""
    hr = MagicMock(name="mock_hybrid_retriever")
    hr.retrieve.return_value = []
    hr.invalidate.return_value = None
    with patch("app.retrieval.hybrid_retriever.get_hybrid_retriever", return_value=hr):
        yield hr


# ── Async HTTP client for FastAPI app ──

@pytest_asyncio.fixture()
async def client(mock_llm, mock_vector_store):
    """AsyncClient wired to the FastAPI app with all externals mocked."""
    # Patch at router-level singletons too
    with (
        patch("app.routers.rag.get_rag_vector_store", return_value=mock_vector_store),
        patch("app.services.question_generation_service.get_rag_vector_store", return_value=mock_vector_store),
        patch("app.services.question_generation_service.chat_llm", mock_llm),
        patch("app.skills.base.skill_llm", mock_llm),
        patch("app.skills.router.chat_llm", mock_llm),
        patch("app.skills.teaching_task_generator.skill.chat_llm", mock_llm),
    ):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
