#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8080"

echo "=========================================="
echo "智能教育平台 API 测试脚本"
echo "=========================================="
echo ""

# 测试1: 登录
echo "【测试1】用户登录"
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

if echo "$RESPONSE" | grep -q '"code":200'; then
    echo -e "${GREEN}✓ 登录成功${NC}"
    TOKEN=$(echo "$RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "Token: ${TOKEN:0:50}..."
else
    echo -e "${RED}✗ 登录失败${NC}"
    echo "响应: $RESPONSE"
    exit 1
fi
echo ""

# 测试2: 获取用户信息
echo "【测试2】获取用户信息"
ME_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/auth/me" \
  -H "Authorization: Bearer $TOKEN")

if echo "$ME_RESPONSE" | grep -q '"code":200'; then
    echo -e "${GREEN}✓ 获取用户信息成功${NC}"
    echo "响应: $ME_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ME_RESPONSE"
else
    echo -e "${RED}✗ 获取用户信息失败${NC}"
    echo "响应: $ME_RESPONSE"
fi
echo ""

# 测试3: 发送聊天消息
echo "【测试3】发送聊天消息"
CHAT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/chat/message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "如何设计一堂数学课？",
    "context": {
      "subject": "数学",
      "grade": "初二"
    }
  }')

if echo "$CHAT_RESPONSE" | grep -q '"code":200'; then
    echo -e "${GREEN}✓ 发送消息成功${NC}"
    CONVERSATION_ID=$(echo "$CHAT_RESPONSE" | grep -o '"conversationId":[0-9]*' | cut -d':' -f2)
    echo "对话ID: $CONVERSATION_ID"
else
    echo -e "${RED}✗ 发送消息失败${NC}"
    echo "响应: $CHAT_RESPONSE"
fi
echo ""

# 测试4: 获取对话列表
echo "【测试4】获取对话列表"
CONV_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/chat/conversations?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN")

if echo "$CONV_RESPONSE" | grep -q '"code":200'; then
    echo -e "${GREEN}✓ 获取对话列表成功${NC}"
else
    echo -e "${RED}✗ 获取对话列表失败${NC}"
fi
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
