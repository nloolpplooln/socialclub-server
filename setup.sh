#!/bin/bash
# ==============================================
#  GTA SocialClub Query — 一键部署脚本
#  用法: chmod +x setup.sh && ./setup.sh
# ==============================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo "============================================"
echo "  GTA SocialClub Query — 一键部署"
echo "============================================"
echo ""

# 检测 Docker
if ! command -v docker &>/dev/null; then
    echo -e "${RED}未检测到 Docker，请先安装: curl -fsSL https://get.docker.com | sh${NC}"
    exit 1
fi

# 配置国内镜像源
sudo mkdir -p /etc/docker
echo '{"registry-mirrors":["https://docker.1ms.run","https://docker.xuanyuan.me"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker 2>/dev/null || sudo service docker restart 2>/dev/null

# 创建数据目录
mkdir -p data

# 检查 cookie
if [ ! -f data/cookie.txt ] || [ ! -s data/cookie.txt ]; then
    echo -e "${YELLOW}未找到 data/cookie.txt${NC}"
    echo ""
    echo "获取方式:"
    echo "  1. 浏览器打开 https://socialclub.rockstargames.com 并登录"
    echo "  2. F5 刷新页面"
    echo "  3. F12 → Application → Cookies → Ctrl+A → Ctrl+C"
    echo "  4. 粘贴到 data/cookie.txt"
    echo ""
    echo "或者先启动容器，再访问 http://<IP>:8686/setup 网页配置"
    echo ""
fi

# 构建并启动
echo -e "${GREEN}构建 Docker 镜像...${NC}"
docker-compose build --quiet

echo -e "${GREEN}启动服务...${NC}"
docker-compose up -d

sleep 2

# 验证
if curl -s http://localhost:8686/health | grep -q "token"; then
    echo ""
    echo -e "${GREEN}部署成功！${NC}"
    echo ""
    echo "  Web 面板:  http://localhost:8686/ui"
    echo "  配置页面:  http://localhost:8686/setup"
    echo "  API 文档:  http://localhost:8686/docs"
    echo ""
else
    echo -e "${YELLOW}容器已启动，正在初始化...${NC}"
    echo "  查看日志: docker logs socialclub-api"
fi