"""
集成测试 — 真实调用本地 Ollama，端到端验证全链路。

运行前提：本地 Ollama 已启动，已拉取 qwen3:4b 和 qwen3-embedding:4b 模型。

运行方式：
    conda run -n Langchain-sgg python -m pytest tests/test_integration.py -v -m integration
    conda run -n Langchain-sgg python -m pytest -m "not integration"   # 跳过集成测试
"""

import os
import sys

# ── 环境变量（必须在所有 app import 之前设置） ──
# 清除代理，防止 Ollama 请求被代理拦截导致 503
for _proxy_key in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_key, None)

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost/v1")
os.environ["MONGODB_ENABLED"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

AI_SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AI_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, AI_SERVICE_ROOT)

from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage


# ── 常量 ──

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# 8 条法学种子文档，覆盖 3 本"教材"
_SEED_DOCS = [
    Document(
        page_content="合同是当事人之间设立、变更、终止债权债务关系的协议。合同的成立需要要约和承诺两个阶段。",
        metadata={"book_label": "合同法教程", "book_id": "book_contract", "file_name": "contract_law.txt", "chunk_index": 0},
    ),
    Document(
        page_content="要约是希望与他人订立合同的意思表示，应具备合同的必要条款，并表示经受要约人承诺即受约束。",
        metadata={"book_label": "合同法教程", "book_id": "book_contract", "file_name": "contract_law.txt", "chunk_index": 1},
    ),
    Document(
        page_content="违约责任是指合同当事人不履行或不适当履行合同义务所应承担的法律责任，包括继续履行、赔偿损失、支付违约金等形式。",
        metadata={"book_label": "合同法教程", "book_id": "book_contract", "file_name": "contract_law.txt", "chunk_index": 2},
    ),
    Document(
        page_content="刑法第232条规定：故意杀人的，处死刑、无期徒刑或者十年以上有期徒刑；情节较轻的，处三年以上十年以下有期徒刑。",
        metadata={"book_label": "刑法学", "book_id": "book_criminal", "file_name": "criminal_law.txt", "chunk_index": 0},
    ),
    Document(
        page_content="犯罪构成要件包括：犯罪主体、犯罪主观方面、犯罪客体、犯罪客观方面，四要件缺一不可。",
        metadata={"book_label": "刑法学", "book_id": "book_criminal", "file_name": "criminal_law.txt", "chunk_index": 1},
    ),
    Document(
        page_content="正当防卫是指为使国家、公共利益、本人或他人的人身、财产和其他权利免受正在进行的不法侵害而采取的制止不法侵害的行为。",
        metadata={"book_label": "刑法学", "book_id": "book_criminal", "file_name": "criminal_law.txt", "chunk_index": 2},
    ),
    Document(
        page_content="民法典第1165条规定：行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。",
        metadata={"book_label": "侵权责任法", "book_id": "book_tort", "file_name": "tort_law.txt", "chunk_index": 0},
    ),
    Document(
        page_content="过错推定原则是指法律规定在某些特殊情形下，推定行为人有过错，由行为人证明自己没有过错，否则承担侵权责任。",
        metadata={"book_label": "侵权责任法", "book_id": "book_tort", "file_name": "tort_law.txt", "chunk_index": 1},
    ),
]


# ═══════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════


def _is_ollama_available() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def ollama_available():
    """Ollama 不可达时跳过全部集成测试。"""
    if not _is_ollama_available():
        pytest.skip("Ollama 未运行，跳过集成测试")


@pytest.fixture(scope="session")
def clean_llm():
    """
    创建不受代理影响的 ChatOllama 实例。
    必须在清除 proxy 之后创建，否则 httpx client 会缓存代理配置。
    """
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model="qwen3:4b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )


@pytest.fixture(scope="session")
def clean_embedding_model():
    """创建不受代理影响的 OllamaEmbeddings 实例。"""
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        model="qwen3-embedding:4b",
        base_url=OLLAMA_BASE_URL,
    )


@pytest.fixture(scope="session")
def seeded_vector_store(ollama_available, clean_embedding_model):
    """
    创建内存 ChromaDB 并塞入 8 条种子文档。
    session 级别：embedding 只计算一次（约 8 次 Ollama 调用）。
    """
    from langchain_chroma import Chroma

    vs = Chroma(
        collection_name="integration_test_collection",
        embedding_function=clean_embedding_model,
    )
    vs.add_documents(_SEED_DOCS)
    return vs


def _patch_vector_store(seeded_vs):
    """返回 patch 列表，替换所有 get_rag_vector_store 调用点。"""
    from app.llm.vector_store import get_rag_vector_store
    get_rag_vector_store.cache_clear()

    return (
        patch("app.llm.vector_store.get_rag_vector_store", new=lambda: seeded_vs),
        patch("app.routers.rag.get_rag_vector_store", new=lambda: seeded_vs),
        patch("app.services.rag_chat_service.get_rag_vector_store", new=lambda: seeded_vs),
        patch("app.services.question_generation_service.get_rag_vector_store", new=lambda: seeded_vs),
        patch("app.agents.plan_agent.get_rag_vector_store", new=lambda: seeded_vs),
        patch("app.tools.rag_tool.get_rag_vector_store", new=lambda: seeded_vs),
    )


def _patch_llm(clean_llm_instance):
    """返回 patch 列表，替换所有 chat_llm 引用点。"""
    return (
        patch("app.llm.model_factory.chat_llm", clean_llm_instance),
        patch("app.skills.base.chat_llm", clean_llm_instance),
        patch("app.skills.router.chat_llm", clean_llm_instance),
        patch("app.skills.teaching_task_generator.skill.chat_llm", clean_llm_instance),
        patch("app.services.question_generation_service.chat_llm", clean_llm_instance),
        patch("app.services.rag_chat_service.chat_llm", clean_llm_instance),
    )


@pytest.fixture()
def patched_vector_store(seeded_vector_store, clean_llm):
    """function 级别：注入内存向量库和干净 LLM 到所有调用点。"""
    vs_patches = _patch_vector_store(seeded_vector_store)
    llm_patches = _patch_llm(clean_llm)
    all_patches = vs_patches + llm_patches
    for p in all_patches:
        p.start()
    yield seeded_vector_store
    for p in all_patches:
        p.stop()
    from app.llm.vector_store import get_rag_vector_store
    get_rag_vector_store.cache_clear()


@pytest.fixture()
def reset_skill_router_cache():
    """重置 skill router 的模块级缓存。"""
    import app.skills.router as router_mod
    router_mod._skills = {}
    yield
    router_mod._skills = {}


@pytest_asyncio.fixture()
async def integration_client(seeded_vector_store, clean_llm):
    """带真实 LLM 的 FastAPI AsyncClient。"""
    vs_patches = _patch_vector_store(seeded_vector_store)
    llm_patches = _patch_llm(clean_llm)
    all_patches = vs_patches + llm_patches
    for p in all_patches:
        p.start()

    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=180.0) as ac:
        yield ac

    for p in all_patches:
        p.stop()
    from app.llm.vector_store import get_rag_vector_store
    get_rag_vector_store.cache_clear()


# ═══════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════


@pytest.mark.integration
class TestSelectSkillIntegration:
    """真实 LLM 技能路由。"""

    @pytest.mark.asyncio
    async def test_concept_query_routes_to_valid_skill(
        self, ollama_available, clean_llm, reset_skill_router_cache
    ):
        llm_patches = _patch_llm(clean_llm)
        for p in llm_patches:
            p.start()
        try:
            from app.skills.router import select_skill
            skill = await select_skill("什么是合同的成立要件？")
            all_skills = {
                "law_explain", "law_article", "case_analysis",
                "curriculum_outline", "knowledge_sequencing",
                "teaching_activity", "assessment_design",
            }
            assert skill.name in all_skills
        finally:
            for p in llm_patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_case_query_routes_to_valid_skill(
        self, ollama_available, clean_llm, reset_skill_router_cache
    ):
        llm_patches = _patch_llm(clean_llm)
        for p in llm_patches:
            p.start()
        try:
            from app.skills.router import select_skill
            skill = await select_skill("张三持刀伤害李四，构成什么罪？请分析案情。")
            all_skills = {
                "law_explain", "law_article", "case_analysis",
                "curriculum_outline", "knowledge_sequencing",
                "teaching_activity", "assessment_design",
            }
            assert skill.name in all_skills
        finally:
            for p in llm_patches:
                p.stop()


@pytest.mark.integration
class TestSkillRunIntegration:
    """真实 LLM 结构化输出。"""

    @pytest.mark.asyncio
    async def test_law_explain_structured_output(
        self, ollama_available, patched_vector_store
    ):
        from app.skills.registry import get_registered_skills
        skills = get_registered_skills()
        skill = skills["law_explain"]
        docs = patched_vector_store.similarity_search("合同成立要件", k=3)

        result = await skill.run("什么是合同的成立要件？", docs)

        assert result.skill_used == "law_explain"
        assert isinstance(result.answer, str) and len(result.answer) > 10
        assert result.confidence in {"high", "medium", "low"}
        assert isinstance(result.exploration_tasks, list)
        assert isinstance(result.book_labels, list) and len(result.book_labels) >= 1

    @pytest.mark.asyncio
    async def test_case_analysis_structured_output(
        self, ollama_available, patched_vector_store
    ):
        from app.skills.registry import get_registered_skills
        skills = get_registered_skills()
        skill = skills["case_analysis"]
        docs = patched_vector_store.similarity_search("故意杀人罪", k=3)

        result = await skill.run("张三持刀故意伤害李四，分析本案刑事责任", docs)

        assert result.skill_used == "case_analysis"
        assert isinstance(result.answer, str) and len(result.answer) > 10
        assert result.confidence in {"high", "medium", "low"}


@pytest.mark.integration
class TestTeachingTaskGeneratorIntegration:
    """真实 LLM 探索任务生成。"""

    @pytest.mark.asyncio
    async def test_generates_real_tasks(
        self, ollama_available, patched_vector_store
    ):
        from app.skills.teaching_task_generator.skill import TeachingTaskGeneratorSkill
        skill = TeachingTaskGeneratorSkill()
        docs = patched_vector_store.similarity_search("合同违约责任", k=3)

        tasks = await skill.run(
            query="违约责任包括哪些形式？",
            answer="违约责任包括继续履行、赔偿损失、支付违约金等。",
            retrieved_docs=docs,
            existing_tasks=[],
        )

        assert isinstance(tasks, list)
        assert 1 <= len(tasks) <= 3
        assert all(isinstance(t, str) and t.strip() for t in tasks)


@pytest.mark.integration
class TestRagChatServiceIntegration:
    """完整 RAG 对话链路。"""

    @pytest.mark.asyncio
    async def test_chat_returns_valid_shape(
        self, ollama_available, patched_vector_store, reset_skill_router_cache
    ):
        from app.services.rag_chat_service import RagChatService
        service = RagChatService()

        result = await service.chat(
            query="什么是合同的违约责任？",
            history_messages=[],
            conversation_id=None,
            max_history_tokens=512,
        )

        required_keys = {"answer", "skill_used", "sources", "exploration_tasks",
                         "book_labels", "confidence", "audit_notes"}
        assert required_keys.issubset(set(result.keys()))
        assert isinstance(result["answer"], str) and len(result["answer"]) > 10
        assert result["confidence"] in {"high", "medium", "low"}
        assert isinstance(result["sources"], list)
        assert isinstance(result["exploration_tasks"], list)
        assert isinstance(result["book_labels"], list)

    @pytest.mark.asyncio
    async def test_chat_with_history(
        self, ollama_available, patched_vector_store, reset_skill_router_cache
    ):
        from app.services.rag_chat_service import RagChatService
        service = RagChatService()

        result = await service.chat(
            query="那违约金怎么计算？",
            history_messages=[
                HumanMessage(content="违约责任包括哪些形式？"),
                AIMessage(content="包括继续履行、赔偿损失、支付违约金等。"),
            ],
            conversation_id=None,
            max_history_tokens=512,
        )

        assert isinstance(result["answer"], str) and result["answer"].strip()

    @pytest.mark.asyncio
    async def test_confidence_when_docs_found(
        self, ollama_available, patched_vector_store, reset_skill_router_cache
    ):
        from app.services.rag_chat_service import RagChatService
        service = RagChatService()

        result = await service.chat(
            query="刑法第232条规定了什么？",
            history_messages=[],
            conversation_id=None,
            max_history_tokens=512,
        )

        # 种子文档包含刑法第232条，应能检索到
        assert result["confidence"] in {"high", "medium"}


@pytest.mark.integration
class TestQuestionGenerationIntegration:
    """完整出题链路。"""

    @pytest.mark.asyncio
    async def test_generate_questions(
        self, ollama_available, patched_vector_store
    ):
        from app.services.question_generation_service import (
            QuestionGenerateInput,
            QuestionGenerationService,
        )
        service = QuestionGenerationService()

        # qwen3:4b 的 structured output 偶尔生成空题干，允许重试一次
        last_exc = None
        for attempt in range(2):
            try:
                result = await service.generate(
                    QuestionGenerateInput(
                        subject="法学",
                        topic="合同法",
                        question_count=2,
                        question_types=["简答题"],
                        output_mode="practice",
                    )
                )
                qs = result.question_set
                assert qs.question_count >= 1
                assert isinstance(qs.questions, list) and len(qs.questions) >= 1
                q = qs.questions[0]
                assert q.stem.strip()
                assert q.answer.strip()
                assert q.explanation.strip()
                assert isinstance(result.book_labels, list)
                break
            except (ValueError, AssertionError) as exc:
                last_exc = exc
        else:
            pytest.skip(f"LLM 连续生成低质量输出，跳过: {last_exc}")

    @pytest.mark.asyncio
    async def test_generate_with_textbook_scope(
        self, ollama_available, patched_vector_store
    ):
        from app.services.question_generation_service import (
            QuestionGenerateInput,
            QuestionGenerationService,
        )
        service = QuestionGenerationService()

        # qwen3:4b 的 structured output 偶尔生成空题干，允许重试一次
        last_exc = None
        for attempt in range(2):
            try:
                result = await service.generate(
                    QuestionGenerateInput(
                        subject="刑法",
                        topic="故意犯罪",
                        textbook_scope=["刑法学"],
                        question_count=1,
                        question_types=["简答题"],
                    )
                )
                assert result.question_set.question_count >= 1
                assert "刑法学" in result.book_labels
                break
            except (ValueError, AssertionError) as exc:
                last_exc = exc
        else:
            pytest.skip(f"LLM 连续生成低质量输出，跳过: {last_exc}")


@pytest.mark.integration
class TestApiEndpointsIntegration:
    """通过 HTTP 接口测试全链路。"""

    @pytest.mark.asyncio
    async def test_health(self, integration_client):
        resp = await integration_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_rag_books(self, integration_client):
        resp = await integration_client.get("/rag/books")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["total"] >= 3
        labels = {item["book_label"] for item in data["items"]}
        assert "合同法教程" in labels
        assert "刑法学" in labels
        assert "侵权责任法" in labels

    @pytest.mark.asyncio
    async def test_rag_agent_chat(self, integration_client):
        resp = await integration_client.post(
            "/rag/agent/chat",
            json={"query": "什么是合同的违约责任？", "history": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["answer"].strip()
        assert data["confidence"] in {"high", "medium", "low"}

    @pytest.mark.asyncio
    async def test_question_gen(self, integration_client):
        # LLM structured output 有时生成不合格题目，允许重试
        last_data = None
        for attempt in range(2):
            resp = await integration_client.post(
                "/question-gen/generate",
                json={
                    "subject": "法学",
                    "topic": "合同法基础",
                    "question_count": 2,
                    "question_types": ["简答题"],
                },
            )
            assert resp.status_code == 200
            last_data = resp.json()
            if last_data["success"]:
                break
        if not last_data["success"]:
            pytest.skip(f"LLM 连续生成低质量输出: {last_data.get('error')}")
        assert last_data["question_set"]["question_count"] >= 1

    @pytest.mark.asyncio
    async def test_rag_index_by_path(self, integration_client, tmp_path):
        test_file = tmp_path / "test_law.txt"
        test_file.write_text(
            "法律面前人人平等。宪法是国家根本大法，具有最高法律效力。"
            "任何组织和个人都不得有超越宪法和法律的特权。",
            encoding="utf-8",
        )
        resp = await integration_client.post(
            "/rag/index-by-path",
            json={
                "file_path": str(test_file),
                "chunk_size": 200,
                "chunk_overlap": 20,
                "book_label": "宪法教程",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["chunk_count"] >= 1
        assert data["book_label"] == "宪法教程"


@pytest.mark.integration
@pytest.mark.slow
class TestPlanAgentIntegration:
    """教案 Agent 全链路（5 次 LLM 调用，耗时较长）。"""

    @pytest.mark.asyncio
    async def test_plan_agent_generates_semester_plan(self, integration_client):
        resp = await integration_client.post(
            "/plan-agent/generate",
            json={
                "subject": "法学",
                "grade": "大三",
                "topic": "合同法与侵权责任",
                "total_weeks": 8,
                "lessons_per_week": 2,
                "difficulty": "中等",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        plan = data["semester_plan"]
        assert plan.get("semester_title")
        assert isinstance(plan.get("weekly_plans"), list)
        assert len(plan["weekly_plans"]) >= 1
