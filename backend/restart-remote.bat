@echo off
rem CrossAIO remote self-restart: kill uvicorn -> wait -> start latest code
cd /d "D:\Claude\crossbot-ai\backend"
echo [%date% %time%] restart-remote invoked >> uvicorn-9000.log
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn*app.main:app*' } | ForEach-Object { Write-Output ('restart-remote kill PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> uvicorn-9000.log 2>&1
timeout /t 3 >nul
call start-uvicorn.bat
