# 智能教育平台 - AI 服务

基于 FastAPI + LangChain 的 AI 服务，提供智能问答、教案生成、作业批阅等功能。

## 技术栈

- **FastAPI**: Web 框架
- **LangChain**: LLM 应用框架
- **OpenAI**: 大语言模型
- **ChromaDB**: 向量数据库 (RAG)

## 快速开始

### 1. 安装依赖

```bash
cd ai-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 OpenAI API Key
```

### 3. 启动服务

```bash
python -m app.main
```

或

```bash
uvicorn app.main:app --reload
```

服务启动后访问：http://localhost:8000/docs

## API 接口

### 智能问答
- `POST /chat/completions` - 通用对话
- `POST /chat/education` - 教育领域问答
- `POST /chat/stream` - 流式对话

### 教案生成
- `POST /lesson-plan/generate` - 生成教案
- `POST /lesson-plan/enhance` - 优化教案

### 作业批阅
- `POST /grading/essay` - 作文批阅
- `POST /grading/code` - 代码批阅
- `POST /grading/math` - 数学题批阅
- `POST /grading/english-essay` - 英语作文批阅

### 知识库
- `POST /knowledge/upload` - 上传文档
- `POST /knowledge/search` - 语义搜索

## Docker 部署

```bash
docker build -t edu-ai-service .
docker run -p 8000:8000 --env-file .env edu-ai-service
```

## 测试

```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}]
  }'
```
