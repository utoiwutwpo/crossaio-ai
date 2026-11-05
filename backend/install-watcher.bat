@echo off
chcp 65001 >nul
echo ============================================
echo  CrossAIO uvicorn watcher - one-time install
echo ============================================
echo.

rem 1) 开机自启任务 1：监视器（轮询 .restart-trigger 触发文件，发现即自动重启 uvicorn）
schtasks /create /tn "CrossAIO_UvicornWatcher" /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File D:\Claude\crossbot-ai\backend\uvicorn-watcher.ps1" /sc onlogon /rl highest /f
if errorlevel 1 goto :err

rem 2) 开机自启任务 2：开机自动拉起 uvicorn 本体
schtasks /create /tn "CrossAIO_UvicornStart" /tr "D:\Claude\crossbot-ai\backend\start-uvicorn.bat" /sc onlogon /f
if errorlevel 1 goto :err

rem 3) 立即启动监视器（无需重启电脑）
schtasks /run /tn "CrossAIO_UvicornWatcher"
if errorlevel 1 goto :err

echo.
echo [OK] Watcher installed and running.
echo      - Trigger file : D:\Claude\crossbot-ai\backend\.restart-trigger
echo      - Watcher log  : D:\Claude\crossbot-ai\backend\watcher.log
echo      - Boot autostart registered (watcher + uvicorn).
echo.
pause
exit /b 0

:err
echo [ERROR] schtasks failed - run this .bat as Administrator.
pause
exit /b 1
