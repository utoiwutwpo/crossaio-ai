@echo off
rem CrossAIO uvicorn launcher (port 9000) - idempotent
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
cd /d "D:\Claude\crossbot-ai\backend"
netstat -ano | findstr /R /C:"LISTENING" | findstr /C:":9000" >nul 2>&1 && exit /b 0
"D:\Claude\crossbot-ai\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 9000 >> "D:\Claude\crossbot-ai\backend\uvicorn-9000.log" 2>&1