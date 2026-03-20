#!/bin/bash

# AI 服务启动脚本

echo "====================================="
echo "智能教育平台 AI 服务"
echo "====================================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -q -r requirements.txt

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，使用默认配置"
    cp .env.example .env
fi

# 清除代理，避免 Ollama 请求走代理导致 503
unset http_proxy HTTP_PROXY https_proxy HTTPS_PROXY all_proxy ALL_PROXY

# 启动服务
echo "启动服务..."
echo "访问 http://localhost:8000/docs 查看 API 文档"
echo "====================================="

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
