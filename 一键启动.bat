@echo off
chcp 65001 >nul
cd /d "%~dp0"
title GTA 玩家查询

echo ========================================
echo   GTA 玩家查询 — 自动安装 & 启动
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [安装] 下载 Python（约 30MB），请稍候...
    curl -L -o python-install.exe "https://mirrors.huaweicloud.com/python/3.12.9/python-3.12.9-amd64.exe"
    echo [安装] 请在弹出的窗口里勾选"Add Python to PATH"然后点 Install
    start /wait python-install.exe
    del python-install.exe
    echo [提示] 安装完 Python 后请重新双击此脚本
    pause
    exit
)

:: 创建虚拟环境
if not exist .venv (
    echo [安装] 创建虚拟环境...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ --upgrade pip
)

:: 安装依赖
echo [安装] 检查依赖...
.venv\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

:: 注入 cookie
if exist cookie.txt (
    echo [配置] 注入 cookie...
    .venv\Scripts\python.exe -m app.cli setckf cookie.txt >nul 2>&1
) else (
    echo [提示] 未找到 cookie.txt，启动后访问 /setup 粘贴配置
)

:: 杀旧端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8686" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1

echo.
echo ========================================
echo   启动完成！浏览器打开:
echo   http://localhost:8686/setup
echo ========================================
echo.

.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8686
pause