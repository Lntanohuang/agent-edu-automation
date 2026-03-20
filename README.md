# Agent Edu Automation — 智能教育平台

本仓库为智能教育平台的**统一代码库**，包含前端、后端与 AI 服务三个子模块，并保留了各自完整的提交历史。

## 项目结构

```
agent-edu-automation/
├── frontend/      # Vue 3 + Vite + TypeScript + Element Plus + Pinia（端口 3000）
├── backend/       # Spring Boot 3.2 + Java 17 + Maven（端口 8080）
└── ai-service/    # Python + FastAPI + LangChain + ChromaDB（端口 8000）
```

## 快速启动

### 前端
```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### 后端
```bash
cd backend
mvn spring-boot:run   # http://localhost:8080
```

### AI 服务
```bash
cd ai-service
# 确保已激活 conda/venv 环境
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 或 ./start.sh
```

## 架构概览

```
Browser → Frontend (:3000)
            ├─► Backend (:8080)  /api 代理
            │     ├─► MySQL / Redis / MongoDB / RabbitMQ
            │     └─► AI Service (:8000)
            └─► AI Service (:8000)  直连（RAG 工作台）
                  ├─► Ollama / OpenAI 兼容 LLM
                  ├─► ChromaDB（本地向量库）
                  └─► MongoDB（对话记忆）
```

## 原始仓库（Gitee，含独立历史）

| 模块 | 原始仓库地址 |
|------|-------------|
| frontend | https://gitee.com/angryfuckxxx/intelligent-education-platform-frontend |
| backend | https://gitee.com/angryfuckxxx/intelligent-education-platform-backend |
| ai-service | https://gitee.com/tenpercentengineer/intelligent-education-platform-aiservice |

> 原始仓库继续保留，本仓库（[agent-edu-automation](https://github.com/Lntanohuang/agent-edu-automation)）为三模块的统一 GitHub 镜像。
