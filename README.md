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

> 本项目支持 **macOS / Linux / Windows** 三大平台。Windows 用户请同时阅读下方 [Windows 用户特别说明](#windows-用户特别说明)。

### 必备组件 — 版本要求与安装命令

| 组件 | 版本要求 | macOS | Windows | Linux (Debian/Ubuntu) |
|---|---|---|---|---|
| **Python** | **3.11.x**（推荐 3.11.9，**不支持 3.12 / 3.13**，部分依赖在新版 Python 下装不上） | `brew install python@3.11` | [python.org 下载 3.11.9](https://www.python.org/downloads/release/python-3119/) | `sudo apt install python3.11 python3.11-venv` |
| **JDK** | **Java 17**（17.x 任一小版本，**勿用 21**） | `brew install openjdk@17` | [Adoptium Temurin 17](https://adoptium.net/temurin/releases/?version=17) | `sudo apt install openjdk-17-jdk` |
| **Maven** | **≥ 3.6.3**（推荐 3.9.x） | `brew install maven` | [maven.apache.org](https://maven.apache.org/download.cgi) 解压后配 `PATH` | `sudo apt install maven` |
| **Node.js** | **18 LTS 或 20 LTS**（勿用奇数版 19/21） | `brew install node@20` | [nodejs.org LTS 安装包](https://nodejs.org/) | `nvm install --lts` |
| **MySQL** | **8.0.x**，字符集 `utf8mb4` | `brew install mysql` | [MySQL Installer](https://dev.mysql.com/downloads/installer/) | `sudo apt install mysql-server-8.0` |
| **Ollama** | 最新稳定版 | `brew install ollama` | [ollama.com/download/windows](https://ollama.com/download/windows) | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **通义千问 API Key** | Dashscope 账号 | 登录 [阿里云百炼](https://bailian.console.aliyun.com/) 开通"模型服务" → 获取 API Key（免费额度足够测试） |||

### 可选组件

| 组件 | 用途 | 不装会怎样 |
|---|---|---|
| Redis | 缓存 | 可跳过，不影响主功能 |
| MongoDB | 对话记忆 / 检索日志 | 优雅降级，启动时日志提示 "MongoDB 未启用" |
| RabbitMQ | 异步消息（目前仅 chat 模块用） | 可跳过 |

### 安装后版本校验

```bash
# macOS / Linux
python3.11 --version   # Python 3.11.x
java -version          # openjdk 17.x
mvn -version           # Apache Maven 3.6.3+
node -v                # v18.x 或 v20.x
mysql --version        # 8.0.x
ollama --version

# Windows 下 Python 用 py 启动器
py -3.11 --version
```

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

macOS / Linux / Windows 命令一致：
```bash
ollama serve            # 启动服务（默认端口 11434）
ollama pull qwen3-embedding:4b   # 首次运行需拉取 Embedding 模型
```

### 2. AI 服务（首次启动）

**创建虚拟环境（三平台分别操作）**

<details>
<summary><b>macOS / Linux</b></summary>

```bash
cd ai-service
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
</details>

<details>
<summary><b>Windows (PowerShell，推荐)</b></summary>

```powershell
cd ai-service
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> 如提示 `无法加载文件...Activate.ps1`，执行一次：
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 后重试。
</details>

<details>
<summary><b>Windows (CMD)</b></summary>

```cmd
cd ai-service
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```
</details>

**启动服务**（三平台均在激活虚拟环境后执行）：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**首次启动需导入法律文档**（另开一个终端，同样激活虚拟环境）：
```bash
python scripts/import_legal_docs.py data/labor_law/
```

> 如果 `pip install` 在 Windows 下报 `Microsoft Visual C++ 14.0 is required`，
> 安装 [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 后重试。

### 3. 后端

```bash
cd backend
mvn spring-boot:run
```

或用 IntelliJ IDEA 打开 `backend/` 目录后直接运行 `EduPlatformApplication`。

> Windows PowerShell 下如果 `mvn` 命令找不到，检查 `MAVEN_HOME` 环境变量和
> `%MAVEN_HOME%\bin` 是否在 `PATH` 中。

### 4. 前端

```bash
cd frontend
npm install        # 首次
npm run dev        # http://localhost:3000
```
三平台命令一致。如 `npm install` 卡住，切换镜像：
```bash
npm config set registry https://registry.npmmirror.com
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

### requirements.txt 说明

`ai-service/requirements.txt` 是**跨平台最小化**依赖清单（约 30 个顶层包），支持 macOS / Linux / Windows 直接 `pip install`。

如果你需要严格复现作者本地开发环境，`ai-service/requirements.conda-freeze.txt` 保留了原始的 conda 环境快照（含本地路径，**仅作参考，不能直接安装**）。

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
| `pip install` 报 `No such file or directory: /home/conda/...` | 旧版 `requirements.txt` 是 conda 环境 freeze，路径指向不存在的构建机 | 已用跨平台最小化版替换；如仍报错，删除 `.venv` 后重建 |
| Windows `Activate.ps1 无法加载` | PowerShell 执行策略限制 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Windows `Microsoft Visual C++ 14.0 is required` | 缺少 C++ 编译工具链 | 安装 [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| MySQL 中文乱码 | 字符集不是 utf8mb4 | 建库时指定 `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` |
| `.env` 读取字段异常、pydantic 报编码错 | Windows 记事本保存为 UTF-8 with BOM | 用 VS Code 另存为 **UTF-8 无 BOM** |

## Windows 用户特别说明

Windows 下跑这个项目有几个坑点，提前知会：

1. **不要用 `start.sh`** — 这是 bash 脚本，Windows 下请按上方[启动流程](#启动流程)逐条手动执行
2. **命令行选择**：推荐 **PowerShell 7+**，它对 `source`、`/` 路径兼容性更好；CMD 也行但命令需改写
3. **Python 启动器**：Windows 用 `py -3.11` 比 `python` 更可靠，避免系统多个 Python 版本打架
4. **路径分隔符**：文档里的 `/` 在 PowerShell 下可直接用，在 CMD 下需改成 `\`
5. **Ollama 端口冲突**：Windows 安装 Ollama 后会自动注册服务占用 11434，如冲突请在"服务"中停掉旧实例或改端口
6. **MySQL 字符集**：安装时务必勾选 `utf8mb4`，否则中文法律文档入库会乱码。建库命令：
   ```sql
   CREATE DATABASE edu_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
7. **`.env` 文件编码**：务必保存为 **UTF-8 无 BOM**。Windows 记事本默认会加 BOM，导致 pydantic 解析首个字段失败。推荐用 VS Code 或 Notepad++ 编辑
8. **长路径限制**：Windows 默认 260 字符路径限制可能触发（尤其 node_modules），建议项目放在 `C:\dev\` 这种短路径下，或启用 [长路径支持](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)
9. **防火墙**：首次启动 8000 / 8080 / 3000 端口时 Windows Defender 会弹窗，选择 "允许访问"
10. **flashrank / chromadb 装不上**：99% 是 Python 版本不对，确认是 3.11.x 而非 3.12+

> Windows 支持基于文档推断和社区反馈，部分场景未经实机全量验证。遇到问题欢迎提 issue。

## 原始仓库（Gitee，含独立历史）

| 模块 | 原始仓库地址 |
|------|-------------|
| frontend | https://gitee.com/angryfuckxxx/intelligent-education-platform-frontend |
| backend | https://gitee.com/angryfuckxxx/intelligent-education-platform-backend |
| ai-service | https://gitee.com/tenpercentengineer/intelligent-education-platform-aiservice |

> 原始仓库继续保留，本仓库（[agent-edu-automation](https://github.com/Lntanohuang/agent-edu-automation)）为三模块的统一 GitHub 镜像。
