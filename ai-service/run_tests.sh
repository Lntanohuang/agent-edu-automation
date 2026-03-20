#!/bin/bash
# 智能教育平台 AI Service — 一键运行全部测试
# 用法:
#   ./run_tests.sh              # 运行全部测试
#   ./run_tests.sh -v           # 详细输出
#   ./run_tests.sh -k "router"  # 只跑包含 "router" 的测试
#   ./run_tests.sh --co         # 列出所有测试用例（不执行）

set -e
cd "$(dirname "$0")"

# 安装测试依赖（如未安装）
pip install pytest pytest-asyncio httpx --quiet 2>/dev/null

echo "=========================================="
echo "  智能教育平台 AI Service — 测试套件"
echo "=========================================="
echo ""

# 设置测试环境变量
export OPENAI_API_KEY="test-key"
export OPENAI_BASE_URL="http://localhost/v1"
export MONGODB_ENABLED="false"
export LANGSMITH_TRACING="false"

python -m pytest "$@"
