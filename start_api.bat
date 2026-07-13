@echo off
cd /d "C:\Users\lenovo\Desktop\ai\socialclub"
start "SocialClub-API" .venv314\Scripts\python.exe -B -m uvicorn app.main:app --host 0.0.0.0 --port 8686
echo SocialClub API started on http://localhost:8686
