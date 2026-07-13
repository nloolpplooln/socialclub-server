@echo off
cd /d "C:\Users\lenovo\AstrBot"
echo Cleaning cache...
rmdir /s /q __pycache__ 2>nul
rmdir /s /q astrbot\__pycache__ 2>nul
for /d /r . %%d in (__pycache__) do @rmdir /s /q "%%d" 2>nul
echo Compiling...
C:\Users\lenovo\Desktop\ai\socialclub\.venv314\Scripts\python.exe -m compileall -q astrbot\ main.py runtime_bootstrap.py 2>nul
echo Starting AstrBot...
start "AstrBot" C:\Users\lenovo\Desktop\ai\socialclub\.venv314\Scripts\python.exe main.py
echo AstrBot started on http://localhost:6185
