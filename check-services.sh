#!/bin/bash
# 本地联调前依赖服务检查脚本

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass=0
fail=0

check_port() {
    local name=$1
    local host=$2
    local port=$3
    if nc -z -w 2 "$host" "$port" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name ($host:$port)"
        ((pass++))
    else
        echo -e "  ${RED}✗${NC} $name ($host:$port)"
        ((fail++))
    fi
}

check_http() {
    local name=$1
    local url=$2
    if curl -s -o /dev/null -w '' --connect-timeout 2 "$url" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name ($url)"
        ((pass++))
    else
        echo -e "  ${RED}✗${NC} $name ($url)"
        ((fail++))
    fi
}

echo ""
echo "========== 依赖服务检查 =========="
echo ""

echo "[基础设施]"
check_port "MySQL"    localhost 3306
check_port "Redis"    localhost 6379
check_port "MongoDB"  localhost 27017

echo ""
echo "[应用服务]"
check_http "AI Service"  "http://localhost:8000/docs"
check_http "Backend"     "http://localhost:8080/actuator/health"
check_port "Ollama"      localhost 11434

echo ""
echo "========== 结果: ${pass} 通过, ${fail} 失败 =========="

if [ $fail -gt 0 ]; then
    echo -e "${YELLOW}提示: 请启动失败的服务后再联调${NC}"
    exit 1
else
    echo -e "${GREEN}所有服务就绪，可以联调${NC}"
    exit 0
fi
