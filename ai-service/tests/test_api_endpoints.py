"""
Integration tests for FastAPI endpoints.
Uses the async client from conftest.py with all externals mocked.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document


# ── Health Check ──


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


# ── RAG /rag/books ──


@pytest.mark.asyncio
async def test_rag_books_empty(client, mock_vector_store):
    mock_vector_store.get.return_value = {"metadatas": []}
    resp = await client.get("/rag/books")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_rag_books_with_data(client, mock_vector_store):
    mock_vector_store.get.return_value = {
        "metadatas": [
            {"book_label": "数据结构", "book_id": "b1", "file_name": "ds.pdf"},
            {"book_label": "数据结构", "book_id": "b1", "file_name": "ds.pdf"},
            {"book_label": "操作系统", "book_id": "b2", "file_name": "os.pdf"},
        ]
    }
    resp = await client.get("/rag/books")
    data = resp.json()
    assert data["success"] is True
    assert data["total"] == 2
    labels = {item["book_label"] for item in data["items"]}
    assert labels == {"数据结构", "操作系统"}
    # 数据结构 has 2 chunks, should come first
    assert data["items"][0]["chunk_count"] == 2


# ── RAG /rag/agent/chat ──


@pytest.mark.asyncio
async def test_rag_agent_chat_success(client, mock_llm):
    """Mock the RagChatService.chat to return a valid result."""
    mock_result = {
        "answer": "这是回答",
        "skill_used": "law_explain",
        "sources": ["教材A"],
        "exploration_tasks": ["任务1"],
        "book_labels": ["教材A"],
        "confidence": "high",
        "audit_notes": ["已核对"],
    }
    with patch("app.routers.rag.rag_chat_service") as mock_svc:
        mock_svc.chat = AsyncMock(return_value=mock_result)
        resp = await client.post("/rag/agent/chat", json={
            "query": "什么是合同法？",
            "history": [],
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["answer"] == "这是回答"
    assert data["skill_used"] == "law_explain"
    assert data["confidence"] == "high"


@pytest.mark.asyncio
async def test_rag_agent_chat_with_history(client):
    mock_result = {
        "answer": "继续回答",
        "skill_used": "case_analysis",
        "sources": [],
        "exploration_tasks": [],
        "book_labels": [],
        "confidence": "medium",
        "audit_notes": [],
    }
    with patch("app.routers.rag.rag_chat_service") as mock_svc:
        mock_svc.chat = AsyncMock(return_value=mock_result)
        resp = await client.post("/rag/agent/chat", json={
            "query": "那判决结果呢？",
            "conversation_id": "conv-123",
            "history": [
                {"role": "user", "content": "讲讲刑法"},
                {"role": "assistant", "content": "刑法是..."},
            ],
            "max_history_tokens": 256,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_rag_agent_chat_error(client):
    with patch("app.routers.rag.rag_chat_service") as mock_svc:
        mock_svc.chat = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        resp = await client.post("/rag/agent/chat", json={"query": "问题"})
    data = resp.json()
    assert data["success"] is False
    assert "LLM timeout" in data["error"]


# ── Question Generation /question-gen/generate ──


@pytest.mark.asyncio
async def test_question_gen_success(client):
    from app.services.question_generation_service import (
        GeneratedQuestion,
        GeneratedQuestionSet,
        QuestionGenerationResult,
    )

    mock_result = QuestionGenerationResult(
        question_set=GeneratedQuestionSet(
            title="测试题集",
            subject="计算机",
            output_mode="practice",
            question_count=1,
            total_score=10,
            questions=[
                GeneratedQuestion(
                    question_id="Q001", question_type="简答题",
                    stem="什么是进程？", answer="执行中的程序",
                    explanation="操作系统概念", score=10,
                )
            ],
        ),
        book_labels=["操作系统"],
        sources=["os.pdf"],
        validation_notes=[],
    )
    with patch("app.routers.question_generation.question_generation_service") as mock_svc:
        mock_svc.generate = AsyncMock(return_value=mock_result)
        resp = await client.post("/question-gen/generate", json={
            "subject": "计算机",
            "topic": "操作系统",
            "question_count": 1,
            "question_types": ["简答题"],
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["question_set"]["question_count"] == 1
    assert data["book_labels"] == ["操作系统"]


@pytest.mark.asyncio
async def test_question_gen_error(client):
    with patch("app.routers.question_generation.question_generation_service") as mock_svc:
        mock_svc.generate = AsyncMock(side_effect=ValueError("知识库为空"))
        resp = await client.post("/question-gen/generate", json={
            "subject": "数学",
            "question_count": 5,
        })
    data = resp.json()
    assert data["success"] is False
    assert "知识库为空" in data["error"]


# ── Plan Agent /plan-agent/generate ──


@pytest.mark.asyncio
async def test_plan_agent_success(client):
    from app.agents.plan_agent import SemesterPlanOutput, WeeklyPlan

    mock_plan = SemesterPlanOutput(
        semester_title="数据结构学期计划",
        subject="计算机",
        grade="大二",
        total_weeks=18,
        lessons_per_week=2,
        textbook_version="通用版",
        difficulty="中等",
        semester_goals=["掌握数据结构"],
        key_competencies=["编程能力"],
        teaching_strategies=["讲授+实践"],
        weekly_plans=[
            WeeklyPlan(
                week=1, unit_topic="绪论",
                objectives=["了解课程"], key_points=["基本概念"],
                difficulties=["抽象思维"], activities=["讲解"],
                homework="预习", assessment="课堂问答",
            )
        ],
        assessment_plan=["期末考试"],
        resource_plan=["教材+PPT"],
    )
    with patch("app.routers.plan_agent._run_plan_pipeline", new_callable=AsyncMock) as mock_pipeline:
        mock_pipeline.return_value = {"structured_response": mock_plan}
        resp = await client.post("/plan-agent/generate", json={
            "subject": "数据结构",
            "total_weeks": 18,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["semester_plan"]["subject"] == "计算机"
    assert len(data["semester_plan"]["weekly_plans"]) == 1


@pytest.mark.asyncio
async def test_plan_agent_error(client):
    with patch("app.routers.plan_agent._run_plan_pipeline", new_callable=AsyncMock) as mock_pipeline:
        mock_pipeline.side_effect = RuntimeError("Ollama 不可用")
        resp = await client.post("/plan-agent/generate", json={
            "subject": "数学",
        })
    data = resp.json()
    assert data["success"] is False
    assert "Ollama 不可用" in data["message"]
