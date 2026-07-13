@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===== GTA SocialClub 查询服务 =====
echo.

:: 1. 首次运行：自动创建虚拟环境
if not exist .venv314\Scripts\python.exe (
    echo [首次运行] 创建虚拟环境...
    python -m venv .venv314
    if errorlevel 1 (
        echo 需要 Python 3.10+，请先安装 https://www.python.org/downloads/
        pause
        exit /b 1
    )
    .venv314\Scripts\python.exe -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
)

:: 2. 注入凭证
if exist cookie.txt (
    echo [1/2] 注入凭证...
    .venv314\Scripts\python.exe -m app.cli setckf cookie.txt
) else (
    echo [提示] 未找到 cookie.txt
    echo   打开 http://localhost:8686/setup 粘贴 Cookie
    echo.
)

:: 3. 杀旧进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8686" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: 4. 启动
echo [2/2] 启动服务...
echo.
echo   Web:   http://localhost:8686/ui
echo   Setup: http://localhost:8686/setup
echo.
.venv314\Scripts\python.exe -B -m uvicorn app.main:app --host 0.0.0.0 --port 8686
pause