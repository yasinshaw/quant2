#!/bin/bash

# 快速样式修复脚本
# 用于解决样式加载问题

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$FRONTEND_DIR"

echo -e "${BLUE}🔧 样式快速修复工具${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查开发服务器是否在运行
if lsof -Pi :3002 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  检测到端口3002有进程运行${NC}"
    read -p "是否停止开发服务器? (y/n): " stop_server
    if [[ $stop_server == "y" || $stop_server == "Y" ]]; then
        echo -e "${GREEN}🛑 停止开发服务器...${NC}"
        lsof -ti:3002 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
fi

echo -e "${GREEN}🧹 清理缓存...${NC}"
rm -rf .next
rm -rf node_modules/.cache
rm -rf .turbo

echo -e "${GREEN}✅ 缓存清理完成${NC}"
echo ""

echo -e "${BLUE}🚀 启动开发服务器...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "提示："
echo "  - 打开浏览器访问 http://localhost:3002"
echo "  - 打开DevTools并禁用缓存"
echo "  - 如有问题，使用 Cmd+Shift+R (Mac) 硬刷新"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

pnpm dev
