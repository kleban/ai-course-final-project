@echo off
chcp 65001 >nul
title Data Story - agent check (closes itself)
cd /d "%~dp0\..\.."
".venv\Scripts\python.exe" -B -u tools\run_steps.py agent-check "Full check::.venv\Scripts\python.exe -B tools\check.py"
exit /b %ERRORLEVEL%
