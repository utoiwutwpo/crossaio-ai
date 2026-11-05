@echo off
rem CrossAIO 干净重启：杀掉所有 uvicorn 进程（含旧版 --reload 父进程），再以最新代码启动
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
cd /d "D:\Claude\crossbot-ai\backend"
echo [%date% %time%] === restart-service begin === >> restart.log
rem 1) 杀掉所有 uvicorn 进程（含 --reload 父子结构）
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn*app.main:app*' } | ForEach-Object { Write-Output ('kill PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> restart.log 2>&1
timeout /t 3 >nul
rem 2) 用最新代码启动（幂等脚本：端口已被占用则直接退出）
call "D:\Claude\crossbot-ai\backend\start-uvicorn.cmd"
echo [%date% %time%] === restart-service end === >> restart.log
