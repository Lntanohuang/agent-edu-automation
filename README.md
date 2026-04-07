# Agent Edu Automation — 智能教育平台

本仓库为智能教育平台的**统一代码库**，包含前端、后端与 AI 服务三个子模块，并保留了各自完整的提交历史。

> **里程碑 v1.0（2026-04-07）**：智能问答、智能教案生成（Multi-Agent Supervisor V2）、智能出题、RAG 知识库全部功能可用，AI 服务默认接入通义千问 `qwen-plus-latest`，内置四层防御机制保障结构化输出稳定性。

## 项目结构

```
agent-edu-automation/
├── frontend/      # Vue 3 + Vite + TypeScript + Element Plus + Pinia（端口 3000）
├── backend/       # Spring Boot 3.2 + Java 17 + Maven（端口 8080）
└── ai-service/    # Python + FastAPI + LangChain + ChromaDB（端口 8000）
```

## 架构概览

```
Browser → Frontend (:3000)
            ├─► Backend (:8080)  /api 代理
            │     ├─► MySQL / Redis / MongoDB / RabbitMQ
            │     └─► AI Service (:8000)
            └─► AI Service (:8000)  直连（RAG 工作台）
                  ├─► 通义千问 qwen-plus-latest（Chat）+ qwen-turbo-latest（Fixer）
                  ├─► Ollama qwen3-embedding:4b（Embedding）
                  ├─► ChromaDB（本地向量库）
                  └─► MongoDB（对话记忆 / 检索日志）
```

## 已实现功能

| 模块 | 路由 | 说明 |
|---|---|---|
| 智能问答 | `/qa` | RAG + Skill Router，支持法条/案例/概念多路召回 |
| 智能教案生成 | `/lesson-plan` | **V2 Multi-Agent Supervisor**：4 个 Skill Agent 并行 + 冲突检测 + Writer 合并，自动落库 `lesson_plans` |
| 智能出题 | `/question-generator` | 教材驱动出题，支持单选/多选/判断/填空/简答/案例分析，草稿待审核 |
| RAG 知识库 | `/rag` | 文档上传、索引管理、混合检索调试 |

## 环境依赖

### 必备
- **Node.js** ≥ 18 + npm
- **Java 17** + Maven
- **Python 3.11+**（AI 服务，项目内置 `.venv311`）
- **MySQL 8.0**（`edu_platform` 数据库）
- **Ollama**（本地 Embedding 模型）
- **通义千问 Dashscope API Key**（Chat 模型）

### 可选
- Redis（缓存）
- MongoDB（对话记忆、检索日志。没有也可启动，优雅降级）
- RabbitMQ（异步消息，目前仅 chat 模块用）

## 配置步骤

### 1. MySQL

```bash
mysql -u root -p < backend/sql/schema.sql
mysql -u root -p edu_platform < backend/sql/V2_add_semester_plan_fields.sql
mysql -u root -p edu_platform < backend/sql/2026-02-24-question-bank.sql
```

默认连接 `localhost:3306`，用户 `root` / `123456`，可在 `backend/src/main/resources/application.yml` 修改。

### 2. Ollama（Embedding 模型）

```bash
# 安装 Ollama: https://ollama.com/download
ollama serve        # 启动服务（默认端口 11434）

# 拉取 Embedding 模型（必须）
ollama pull qwen3-embedding:4b
```

> **为什么 Embedding 用 Ollama 而非 Dashscope？** ChromaDB 已用 Ollama 索引了语料，切换 Embedding 模型会导致向量维度不兼容，需要全量重新索引。保留本地 Embedding 避免这个问题。

### 3. AI 服务环境变量

在 `ai-service/` 目录创建 `.env`（或复制 `.env.example`）：

```env
# 通义千问 API Key（必须）
OPENAI_API_KEY=sk-xxx

# 以下为默认值，可按需覆盖
CHAT_PROVIDER=qwen_api
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus-latest
FIXER_MODEL=qwen-turbo-latest

# Embedding（默认 ollama）
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b

# Token 配额（四层防御的第 1 层 provider-aware max_tokens）
OPENAI_MAX_TOKENS=2000          # 普通 RAG 问答
SKILL_MAX_TOKENS=4000           # Skill 执行
PLAN_AGENT_MAX_TOKENS=8000      # 教案生成（qwen-plus 上限 8192）

# MongoDB 可选
MONGODB_ENABLED=true
MONGODB_URI=mongodb://127.0.0.1:27017
```

### 4. 通义千问 API 申请

1. 登录 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 开通"模型服务"→获取 API Key
3. 确认以下模型可用：
   - `qwen-plus-latest`（Chat 主力，支持 8192 tokens 输出）
   - `qwen-turbo-latest`（Fixer 用，便宜快速修复 JSON 格式）

## 启动流程

**按顺序启动**：Ollama → MySQL → AI 服务 → 后端 → 前端

### 1. Ollama（保持后台运行）
```bash
ollama serve
```

### 2. AI 服务
```bash
cd ai-service
source .venv311/bin/activate     # 或 conda activate <env>
pip install -r requirements.txt   # 首次
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

首次启动需导入法律文档：
```bash
python scripts/import_legal_docs.py data/labor_law/
```

### 3. 后端
```bash
cd backend
mvn spring-boot:run
# 或用 IntelliJ 直接运行 EduPlatformApplication
```

### 4. 前端
```bash
cd frontend
npm install        # 首次
npm run dev        # http://localhost:3000
```

### 5. 默认账号

由 `DataInitializer` 启动时自动创建：
- `admin` / `admin123`
- `teacher001` / `teacher123`
- `test` / `test123`

## 开发者备忘

### 四层防御机制（`ai-service/app/llm/`）

qwen-plus 不支持严格 `json_schema` 模式，故所有结构化输出调用使用：

1. **Provider-aware method** — `structured_output.py::get_structured_output_method()`：OpenAI 用 `json_schema`，qwen/ollama 降级为 `json_mode`
2. **严格 prompt 约束** — 开头"违反将导致系统解析失败"，结尾"再次警告"
3. **Pydantic 容错 validators** — `unwrap_nested`（解包容器对象）+ `field_validator`（str→list/list→str 自动转换）
4. **小模型修复兜底** — `output_fixer.py::try_parse_with_fix()` 调用 `qwen-turbo-latest` 修复不合规 JSON

适用于 `Skill.run()` / `SkillAgent.run()` / `plan_agent` / `supervisor_agent.writer_node` / `question_generation_service`。

### 超时配置

全链路超时对齐 10 分钟（教案生成最长 ~7 分钟）：
- 前端 axios `timeout: 600000`
- Java `RestTemplate.readTimeout: Duration.ofMinutes(10)`
- AI 服务 `httpx.Client(timeout=300.0)` + `ChatOpenAI(timeout=300)`

### 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| `Broken pipe` 或前端 504 | 前端 timeout 太短 | 已修，升到 600s |
| `Apparent connection leak` (Hikari) | 长耗时 AI 调用被 `@Transactional` 包住 | 已修，拆开事务边界 |
| `LengthFinishReasonError` | max_tokens 不够 | 已拆分 `chat_llm/skill_llm/plan_llm` 三档 |
| Pydantic `validation error` | qwen-plus 结构化输出不稳定 | 四层防御兜底 |
| Ollama 503 | 系统代理污染 httpx | `trust_env=False` 已配置 |

## 原始仓库（Gitee，含独立历史）

| 模块 | 原始仓库地址 |
|------|-------------|
| frontend | https://gitee.com/angryfuckxxx/intelligent-education-platform-frontend |
| backend | https://gitee.com/angryfuckxxx/intelligent-education-platform-backend |
| ai-service | https://gitee.com/tenpercentengineer/intelligent-education-platform-aiservice |

> 原始仓库继续保留，本仓库（[agent-edu-automation](https://github.com/Lntanohuang/agent-edu-automation)）为三模块的统一 GitHub 镜像。
