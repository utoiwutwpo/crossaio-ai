@echo off
rem CrossAIO uvicorn launcher - run from backend dir, log to uvicorn-9000.log
rem Logic: probe whether the running instance is current code (/api/v1/community/platforms -> 404 = stale)
rem         -> kill every uvicorn process -> start again with the latest code.
cd /d "D:\Claude\crossbot-ai\backend"
set PY=.venv\Scripts\python.exe
if not exist "%PY%" set PY=..\.venv\Scripts\python.exe
if not exist "%PY%" set PY=D:\Claude\crossbot-ai\.venv\Scripts\python.exe
if not exist "%PY%" (
  echo [%date% %time%] FATAL: no venv python found >> uvicorn-9000.log
  exit /b 3
)

echo [%date% %time%] start-uvicorn.bat invoked >> uvicorn-9000.log
rem ---- 1) probe stale code ----
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:9000/api/v1/community/platforms > "%TEMP%\cb_code.txt" 2>nul
set /p CODE=<"%TEMP%\cb_code.txt"
echo [%date% %time%] probe code=[%CODE%] >> uvicorn-9000.log
if "%CODE%"=="404" (
  echo [%date% %time%] stale code detected - killing uvicorn processes >> uvicorn-9000.log
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn*app.main:app*' } | ForEach-Object { Write-Output ('kill PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> uvicorn-9000.log 2>&1
  timeout /t 3 >nul
)

rem ---- 2) idempotent: exit when :9000 is still taken ----
netstat -ano | findstr ":9000" | findstr "LISTENING" >nul 2>&1 && exit /b 0

rem ---- 3) start with the latest code (no --reload: it leaves stale parent processes behind) ----
echo [%date% %time%] starting uvicorn (latest code) >> uvicorn-9000.log
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 9000 >> uvicorn-9000.log 2>&1
echo [%date% %time%] uvicorn EXITED code=%errorlevel% >> uvicorn-9000.log
