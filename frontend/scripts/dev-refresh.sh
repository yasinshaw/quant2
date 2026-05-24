#!/bin/bash

# 开发环境资源刷新脚本
# 用于解决Next.js开发时资源不重新加载的问题

set -e

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$FRONTEND_DIR"

echo "🧹 清理前端缓存..."
echo "📁 工作目录: $FRONTEND_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否在frontend目录
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ 错误: 未找到package.json，请确保在frontend目录运行${NC}"
    exit 1
fi

# 清理函数
clean_cache() {
    echo -e "${YELLOW}🗑️  清理Next.js构建缓存...${NC}"
    rm -rf .next

    echo -e "${YELLOW}🗑️  清理node_modules缓存...${NC}"
    rm -rf node_modules/.cache

    echo -e "${YELLOW}🗑️  清理Turbo缓存...${NC}"
    rm -rf .turbo

    echo -e "${GREEN}✅ 缓存清理完成！${NC}"
}

# 交互式菜单
echo ""
echo "请选择操作:"
echo "1) 完全清理并重新启动开发服务器"
echo "2) 仅清理缓存"
echo "3) 重新启动开发服务器（不清理）"
echo "4) 退出"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        clean_cache
        echo -e "${GREEN}🚀 启动开发服务器...${NC}"
        pnpm dev
        ;;
    2)
        clean_cache
        echo -e "${GREEN}✨ 完成！现在可以手动运行 'pnpm dev' 启动服务器${NC}"
        ;;
    3)
        echo -e "${GREEN}🚀 启动开发服务器...${NC}"
        pnpm dev
        ;;
    4)
        echo "👋 再见！"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac
