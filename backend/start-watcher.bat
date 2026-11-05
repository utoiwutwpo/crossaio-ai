@echo off
rem CrossAIO watcher launcher (robust): starts the self-healing watcher and verifies it actually runs
cd /d "%~dp0"
where powershell.exe >nul 2>&1
if errorlevel 1 (
  echo FATAL: powershell.exe not found in PATH >> "%~dp0watcher.log"
  exit /b 1
)
start "" /b powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uvicorn-watcher.ps1" >> "%~dp0watcher-stdout.log" 2>&1
timeout /t 5 >nul
if exist "%~dp0watcher.log" (
  echo Watcher started OK. Log: %~dp0watcher.log
) else (
  echo WARNING: watcher.log missing - see %~dp0watcher-stdout.log
)
exit /b 0
