@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   GTA SocialClub Query - Docker 一键启动
echo ============================================
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop 未运行，请先启动
    echo 安装: https://www.docker.com/products/docker-desktop/
    echo 安装后 Settings - Docker Engine 加镜像源:
    echo "registry-mirrors": ["https://docker.1ms.run"]
    pause
    exit /b 1
)

:: 已有容器直接启动
docker inspect socialclub-api >nul 2>&1
if not errorlevel 1 (
    echo 容器已存在，启动中...
    docker start socialclub-api
    goto done
)

:: 构建镜像
echo 首次运行，构建镜像（需几分钟）...
docker build -t socialclub-api .
if errorlevel 1 (
    echo 构建失败
    pause
    exit /b 1
)

:: 启动
echo 启动容器...
docker run -d --name socialclub-api -p 8686:8686 socialclub-api

:done
echo.
echo ============================================
echo   部署成功！
echo   打开 http://localhost:8686/setup
echo   粘贴 Cookie 即可使用
echo ============================================
pause