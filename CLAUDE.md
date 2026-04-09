# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Intelligent Education Platform (智能教育平台) — a three-module monorepo combining a Vue 3 frontend, Spring Boot backend, and Python/FastAPI AI service with RAG capabilities. The platform serves teachers with AI-powered Q&A, lesson plan generation, and question generation features focused on Chinese labor law / legal education content.

**v1.0 milestone (2026-04-07)**: All four features (智能问答 / 智能教案生成 V2 / 智能出题 / RAG 知识库) are functional. Chat LLM defaults to 通义千问 `qwen-plus-latest` via Dashscope OpenAI-compatible API. Embeddings remain on local Ollama `qwen3-embedding:4b` to preserve ChromaDB index compatibility.

## Architecture

```
Browser → Frontend (:3000)
            ├─► Backend (:8080)  via /api proxy
            │     ├─► MySQL / Redis / MongoDB
            │     │   (RabbitMQ optional, feature-flagged off by default)
            │     └─► AI Service (:8000)
            └─► AI Service (:8000)  direct (RAG workspace)
                  ├─► Dashscope qwen-plus-latest (chat) + qwen-turbo-latest (fixer)
                  ├─► Ollama qwen3-embedding:4b (embedding only)
                  ├─► ChromaDB (local vector store)
                  └─► MongoDB (chat history, retrieval_logs, feedback)
```

## Common Commands

### Frontend (`frontend/`)
```bash
npm install           # Install dependencies
npm run dev           # Dev server at http://localhost:3000
npm run build         # Type-check (vue-tsc) then Vite build
npm run preview       # Preview production build
```

### Backend (`backend/`)
```bash
mvn spring-boot:run          # Dev server at http://localhost:8080
mvn clean package            # Build JAR
mvn test                     # Run tests (no Maven wrapper — uses system mvn)
backend/test-api.sh          # curl-based smoke test (login → get user → chat)
```

Database schema: `backend/sql/schema.sql` (ddl-auto: none — manual schema management). V2 migration: `backend/sql/V2_add_semester_plan_fields.sql` adds `semester_plan_json` / `agent_meta_json` columns to `lesson_plans`.

### AI Service (`ai-service/`)
```bash
# Cross-platform venv setup (Python 3.11.x required, not 3.12+)
python3.11 -m venv .venv
source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Or use the helper (detects SCRIPT_DIR, no hardcoded paths):
./start.sh

# Tests
./run_tests.sh               # Run all tests
./run_tests.sh -k "router"   # Filter by test name
pytest -m "not integration"  # Skip tests requiring local Ollama

# Bulk-load legal documents into ChromaDB (required before RAG queries work)
python scripts/import_legal_docs.py data/labor_law/

# Eval harness
python -m tests.eval.run_eval        # Full evaluation
python -m tests.eval.run_eval_fast   # Fast variant
python -m tests.eval.run_ab_eval     # A/B comparison
```

Test environment automatically sets: `OPENAI_API_KEY=test-key`, `MONGODB_ENABLED=false`, `LANGSMITH_TRACING=false`. Conftest also clears proxy env vars (`http_proxy`, `HTTP_PROXY`, etc.) to prevent Ollama from routing through system proxies.

Pytest markers: `@pytest.mark.integration` (requires Ollama), `@pytest.mark.slow` (long-running).

Pre-integration smoke check: run `./check-services.sh` at repo root to verify all dependent ports (MySQL/Redis/MongoDB/Ollama/backend/ai-service) are up.

## Module-Specific Architecture

### Frontend — Vue 3 + TypeScript + Element Plus + Pinia

- **Strict TypeScript**: `noUnusedLocals`, `noUnusedParameters` enabled — unused variables fail the build
- **Two axios instances** in `src/api/index.ts`: `api` (backend :8080) and `aiApi` (AI service :8000). Both unwrap `.data` in response interceptors. `api` redirects to `/login` on 401/403; `aiApi` does not
- **Timeout**: both axios instances use `timeout: 600000` (10 min) to accommodate long-running lesson plan generation
- **Response normalization**: `normalizeApiResult` + skill-specific normalizers in `api/index.ts` map AI service snake_case payloads (e.g., `semester_plan`) to camelCase expected by Vue components
- **API base URLs configurable** via `VITE_API_BASE_URL` (default: `http://localhost:8080/api`) and `VITE_AI_SERVICE_BASE_URL` (default: `http://localhost:8000`)
- Vite proxy rewrites `/api/*` → `http://localhost:8080/` (strips `/api` prefix) during dev only
- Auth: Bearer token in localStorage, auto-attached via request interceptor. Only `/login` has `meta: { public: true }`
- Routes: `/dashboard`, `/qa`, `/lesson-plan` (→ LessonPlanGeneratorV2), `/rag`, `/question-generator`. V1 legacy at `/lesson-plan-v1-legacy`
- Pinia stores: `chat.ts` (conversations/messages), `lessonPlan.ts` (plan generation, in-memory only)
- Theme system: CSS variables with light/dark via `data-theme` attribute on `<html>`, persisted in `ui-theme-mode` localStorage key
- Path alias: `@/` → `src/`
- Auto-login for dev: `VITE_AUTO_LOGIN=true`, `VITE_DEFAULT_USERNAME`, `VITE_DEFAULT_PASSWORD`

### Backend — Spring Boot 3.2 + Java 17 + JPA

- **Base package**: `com.edu.platform` with standard layering: controller → service → repository → entity
- **Controllers**: AuthController (`/api/auth`), ChatController (`/api/chat`), PlanAgentController (`/api/plan-agent`), PlanAgentV2Controller (`/api/plan-agent/v2`), QuestionBankController (`/api/question-bank`)
- **JWT auth**: Stateless, BCrypt passwords, 2h token expiry, 7d refresh. `JwtAuthenticationFilter` validates on every request. Public endpoints: `/api/auth/login`, `/api/auth/register`, `/api/auth/refresh`, `/actuator/health`
- **DataInitializer**: Seeds admin/teacher/test users on startup (CommandLineRunner)
- **Response format**: `Result<T>` wrapper with `{code, message, data, timestamp}`. `GlobalExceptionHandler` + `BusinessException` for structured errors; `ClientAbortException` handler downgraded to debug to suppress noise from long-running SSE/HTTP disconnects
- **AI integration**: `AiModelClient` (RestTemplate, 180s read timeout) directly calls `http://localhost:8000/rag/agent/chat`; `PlanAgentService` calls `http://localhost:8000/plan-agent/v2/generate` (10 min timeout)
- **Chat architecture (v1.0)**: `ChatService.sendMessage()` is **sync-direct** — receives request, calls `AiModelClient`, archives via `ChatMongoArchiveService`, returns response. Every step emits structured logs with `traceId`. The old MQ-based async path (`ChatEventPublisher` / `UserMessageConsumer` / `AiReplyDeliveryConsumer` / `AiReplyPersistConsumer`) still exists but is guarded by `@ConditionalOnProperty("chat.mq.enabled", havingValue="true")` and disabled by default. `EduPlatformApplication` excludes `RabbitAutoConfiguration` so the app boots without RabbitMQ installed
- **Transaction boundaries**: Long-running AI calls are deliberately NOT wrapped in `@Transactional` (see `QuestionBankService.generate()` / `PlanAgentService`) to avoid Hikari connection leaks. DB persistence runs in a separate private method with JPA's default short transaction
- Database: MySQL (localhost:3306/edu_platform). Schema has 8 tables; `users`, `conversations`, `messages`, `lesson_plans`, `question_generation_drafts`, `question_bank_items` have JPA entities. Password / username for dev: `root` / `123456`
- Uses Fastjson2 (alibaba) for explicit JSON operations alongside Jackson from Spring Boot

### AI Service — FastAPI + LangChain + ChromaDB

This is the most complex module. Key subsystems:

**Request Tracing** (`app/core/middleware.py`): `RequestTraceMiddleware` injects `trace_id` (from `x-trace-id` header or auto-generated 16-char hex) into a `ContextVar`. `get_traced_logger(name)` in `app/core/logging.py` auto-binds trace_id so structured logs throughout the pipeline stay correlated without manual plumbing.

**Exception Hierarchy** (`app/core/exceptions.py`): `EduPlatformError` base → `LLMError`, `RetrievalError`, `SkillError`, `ValidationError`, `DocumentIngestionError`. Each carries `message` + `detail: dict`.

**RAG Pipeline** (orchestrated by `app/services/rag_chat_service.py`):
```
Query → QueryAnalyzer → HybridRetriever → RetrievalValidator → SkillRouter → SkillExecution
      → SourceAudit → Response
```

**Hybrid Retrieval** (`app/retrieval/hybrid_retriever.py`): 4-path fusion + HyDE sub-path + legal reference graph expansion, with RRF scoring:
1. **rule**: regex pattern matching for legal article references (e.g., "劳动合同法第47条") + metadata/content cross-check
2. **bm25**: jieba tokenization (with legal domain dictionary at `data/jieba_legal_dict.txt`) + BM25Okapi
3. **meta**: ChromaDB metadata filter (e.g., `doc_type=statute`)
4. **dense**: Ollama embedding → ChromaDB similarity search. Uses `analysis.expanded_query` (synonym-expanded) instead of raw query
5. **HyDE sub-path** (attached to dense when `analysis.hyde_enabled`): LLM generates hypothetical answer, re-embeds for search
6. **Legal cross-reference expansion** (post-fusion, law_article intent only): `LegalReferenceGraph` follows 依照/按照/根据/违反 citation links between articles

RRF weights are **dynamic** — chosen per query intent from `_RRF_PROFILES` in `query_analyzer.py`. E.g., `law_article_exact` uses `{rule:3.0, bm25:1.5, meta:1.0, dense:0.3}`, `concept_explain` uses `{rule:0.3, bm25:0.6, meta:0.5, dense:2.0}`. Per-path recall `k` is also scaled by the weight.

The retriever is a **singleton** (`get_hybrid_retriever()`) with a threading lock for BM25 index rebuilds. Call `invalidate()` after indexing new documents.

**Query Analysis** (`app/retrieval/query_analyzer.py`): Pure-regex intent detection (`law_article | case_lookup | concept_explain | general`), entity extraction, law-name alias normalization (`_LAW_ALIASES`), synonym expansion (`_SYNONYM_MAP`), metadata filter derivation, dynamic RRF profile selection — zero LLM calls. Oral expressions like "朋友借钱不还" typically fall through to `general` (the LLM rewriter in the validator loop picks them up).

**Retrieval Validation** (`app/retrieval/retrieval_validator.py`): LLM-based relevance grading on top-3 docs after retrieval. If <1 relevant, calls `rewrite_query` LLM to rephrase, re-runs `analyze_query` + full 5-path retrieval. `max_retries=1` (total 2 rounds). On exhaustion: logs warning and returns the last batch (no exception raised — downstream SourceAudit catches hallucinations). Worst case: 7 extra LLM calls per turn (3 grade + 1 rewrite + 3 re-grade).

**Reranking** (`app/retrieval/reranker.py`): FlashRank cross-encoder (`ms-marco-MultiBERT-L-12`) with 512-char sliding window + max-score aggregation. Fallback to jieba keyword matching if FlashRank unavailable. **MMR diversity rerank** (`lambda=0.7`) using jieba-bag Jaccard similarity runs after the relevance rerank to prevent top-k from being dominated by near-duplicate chunks of the same legal article.

**Skill System** (`app/skills/`): **Config-driven** — all skills share a single `Skill` runner (`app/skills/base.py`), each skill directory provides a `SkillConfig` with `{name, description, output_schema, system_prompt, format_answer, default_tasks}`. Skills: `law_article`, `case_analysis`, `concept_explain`, `law_explain`, `teaching_task_generator`, `source_audit`, `curriculum_outline`, `assessment_design`, `teaching_activity`, `knowledge_sequencing`. Registry auto-discovery via `get_registered_skills()`. `SkillRouter` (`app/skills/router.py`) uses an LLM to pick one skill per query for the RAG Q&A flow.

**LLM Providers** (`app/llm/model_factory.py`): Chat via OpenAI-compatible endpoint (Dashscope qwen-plus-latest by default) with `httpx.Client(trust_env=False, timeout=300.0)` to bypass system proxies. **Three tiers of ChatOpenAI instances** (separate instances required because `.with_structured_output(method="json_schema")` internally rebinds and discards prior `max_tokens` bindings):
- `chat_llm` — 2000 tokens, general RAG QA + validator/router
- `skill_llm` — 4000 tokens, skill execution
- `plan_llm` — 8000 tokens, SupervisorPlanAgent writer node (qwen-plus max output is 8192)

Embeddings via Ollama `qwen3-embedding:4b` (never switch — ChromaDB is already indexed with these vectors; swapping embeds requires full reindex). MLX local provider still supported via `CHAT_PROVIDER=mlx`.

**Four-Layer Structured Output Defense** (`app/llm/structured_output.py` + `output_fixer.py`): qwen-plus does NOT support strict `json_schema` mode, so all structured output calls use:
1. **Provider-aware method** — `get_structured_output_method()` returns `json_schema` for OpenAI, `json_mode` for qwen/ollama
2. **Strict prompt constraints** — `build_format_constrained_system_prompt` prepends 【严格格式要求 - 违反将导致系统解析失败】 and `build_format_constrained_human_suffix` re-emphasizes at the end
3. **Pydantic tolerance validators** — `unwrap_nested` model_validator (unwraps qwen's habit of wrapping output in a container dict) + `field_validator`s for common type coercions (str→list, list→str)
4. **Small-model fix fallback** — `try_parse_with_fix()` catches `ValidationError`, sends the broken JSON + schema to `qwen-turbo-latest` (cheap/fast) to repair, re-parses

Applied to: `Skill.run()`, `SkillAgent.run()`, `plan_agent`, `supervisor_agent.writer_node`, `question_generation_service`.

**Document Ingestion**: Two paths:
- HTTP upload (`/rag/index-by-file`): Handles `.pdf`, `.txt`, `.docx` only (not `.md`)
- Bulk script (`scripts/import_legal_docs.py`): Handles `.md` files with legal-aware splitting (statute article-by-article, case structural sections, contract clause-by-clause)

Chunking: `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=200) → ChromaDB with stable chunk IDs (`{book_id}_{index}_{sha1[:12]}`), batch size 32.

**Conversation Memory** (`app/memory/`): MongoDB-backed chat history with in-memory LRU summarization (triggers every 5 user turns, max 512 tokens, max 500 conversations). Summaries lost on restart; MongoDB stores raw messages only. Graceful degradation if MongoDB unavailable.

**Configuration**: Pydantic BaseSettings loading from `.env` file (`app/core/config.py`). `.env.example` exists in `ai-service/` as a template.

**Observability**: LangSmith tracing via `@traceable` decorator (`app/core/tracing.py`). Retrieval telemetry written to MongoDB `retrieval_logs` collection per query.

**MongoDB collections** (database: `ai_service`):
- `rag_chat_messages` — per-turn conversation history
- `feedback` — user helpfulness ratings
- `retrieval_logs` — retrieval telemetry (intent, doc counts, scores, latency, rrf_weights)

**Lesson Plan Generation — SupervisorPlanAgent** (`app/agents/supervisor_agent.py`): LangGraph StateGraph with three nodes:
1. **supervisor_node**: Parallel-dispatches 4 hardcoded skills (`curriculum_outline`, `knowledge_sequencing`, `teaching_activity`, `assessment_design`) via `asyncio.gather(return_exceptions=True)`. `execute_skill_with_retry` wraps each call with `max_retries=2`; on exhaustion marks `status="degraded"` without blocking the others
2. **conflict_detect_node**: Rule-based checks first (e.g., `total_weeks` mismatch between curriculum_outline and knowledge_sequencing) then LLM semantic check between `teaching_activity` and `assessment_design` texts
3. **writer_node**: Merges all skill outputs according to hardcoded `MERGE_PRIORITY` (not LLM-decided), annotates degraded sections as `[数据缺失]` and conflicts as explicit notices. Uses `plan_llm` (8000 tokens) + full four-layer defense to produce `SemesterPlanOutput`

Returns `{structured_response, agent_meta}` where `agent_meta` contains `skill_status`, `conflicts`, `data_gaps`, `merge_priority`, `total_time_ms`. Persisted to MySQL `lesson_plans.semester_plan_json` / `agent_meta_json`.

**Question Generation** (`app/services/question_generation_service.py`): Router overrides `include_answer=True`, `include_explanation=True`, `require_source_citation=True` regardless of frontend input (server-side enforced). `textbook_scope` filters ChromaDB retrieval by `book_label` metadata. Domain is law (`劳动法`), question types include `单选题/多选题/判断题/填空题/简答题/案例分析题`. Uses `skill_llm` + four-layer defense. `answer` field has a `field_validator` coercing list→comma-joined string (qwen-plus sometimes returns `["A","B","C","D"]` for multi-choice).

**Timeout alignment** (full chain 10 min, lesson plan can take ~7 min):
- Frontend axios `timeout: 600000`
- Java `RestTemplate.readTimeout: Duration.ofMinutes(10)` (PlanAgentService) / 180s (AiModelClient for chat)
- AI service `httpx.Client(timeout=300.0)` + `ChatOpenAI(timeout=300)`

**API Routes**: `/rag` (RAG Q&A + indexing), `/plan-agent` + `/plan-agent/v2` (lesson plans), `/question-gen` (question generation), `/feedback` (user feedback). Swagger docs at `/docs` when `debug=true`.

## Infrastructure Notes

- No CI/CD pipelines, no docker-compose
- `ai-service/requirements.txt` is now a **cross-platform minimal** requirements file (~30 top-level pinned packages). The original conda-frozen lock is archived as `requirements.conda-freeze.txt` for reference only — do NOT install from it
- `ai-service/.env.example` exists with qwen-plus-latest defaults
- Root `.gitignore` covers Python/Java/Node/IDE/OS/project artifacts; `.env` is at highest priority to prevent secret leaks
- No Maven wrapper — uses system `mvn`
- Windows support: `start.sh` uses `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"` for portability. Python venv activation differs per platform (see README)
