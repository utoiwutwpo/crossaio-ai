@echo off
rem CrossAIO 一键推送 GitHub（使用本机已保存的 GitHub 凭据）
cd /d "D://Claude//crossbot-ai"
echo ==== 推送前状态 ====
git log --oneline -1
git push origin main
echo.
echo ==== 完成。如上方显示 rejected/需要登录，请按提示操作 ====
pause
