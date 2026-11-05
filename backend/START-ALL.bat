@echo off
rem CrossAIO one-click launcher: clean restart (kill stale uvicorn + start latest code) + self-healing watcher
chcp 65001 >nul
title CrossAIO Service Launcher
cd /d D:\Claude\crossbot-ai\backend

rem ---- 自提升到管理员：否则无法结束以管理员身份启动的旧 uvicorn 进程 ----
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting administrator rights ...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b 0
)

echo [1/6] Stopping every uvicorn process (stale code / --reload parents) ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn*app.main:app*' } | ForEach-Object { Write-Output ('  kill PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 >nul

echo [2/6] Clearing stale restart trigger ...
if exist .restart-trigger del .restart-trigger

echo [3/6] Starting uvicorn with the latest code ...
start "CrossAIO-uvicorn-9000" cmd /c "%~dp0start-uvicorn.cmd"

echo [4/6] Starting self-healing watcher (hidden) ...
call "%~dp0start-watcher.bat"

echo [5/6] Health check in 12s ...
timeout /t 12 >nul
curl -s -o nul -w "health -> HTTP %%{http_code}\n" http://127.0.0.1:9000/health
curl -s -o nul -w "external -> HTTP %%{http_code}\n" http://100.124.185.46:9000/health

echo.
if exist "%~dp0watcher.log" (echo   Watcher: RUNNING - it auto-restarts uvicorn if the service dies.) else (echo   Watcher: NOT running - service will not self-heal.)
echo   HTTP 200  = OK. You can close THIS window.
echo              Keep "CrossAIO-uvicorn-9000" open.
echo   Other     = the watcher retries every 15s; check uvicorn-9000.log for details.
echo.
pause
