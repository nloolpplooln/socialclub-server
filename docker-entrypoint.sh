#!/bin/bash
set -e

echo "============================================"
echo "  GTA SocialClub Query"
echo "============================================"
echo ""

# 如果 data/cookie.txt 存在，自动注入
if [ -f /app/data/cookie.txt ] && [ -s /app/data/cookie.txt ]; then
    echo "[setup] 检测到 cookie.txt，自动注入..."
    python -m app.cli setckf /app/data/cookie.txt 2>/dev/null && echo "[setup] 注入成功" || echo "[setup] 注入失败（可能已过期）"
else
    echo "[setup] 未检测到 cookie，请访问 http://<IP>:8686/setup 粘贴配置"
fi

echo ""
echo "[server] 启动服务..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8686