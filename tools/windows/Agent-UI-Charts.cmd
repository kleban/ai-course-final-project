@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
set NO_PROXY=127.0.0.1,localhost
set PLAYWRIGHT_BROWSERS_PATH=%~dp0..\..\tmp\playwright-browsers
set PYTHONDONTWRITEBYTECODE=1
cd /d "%~dp0\..\.."
set LOG=tmp\verify-132\charts-smoke.log
if exist tmp\verify-132\charts rd /s /q tmp\verify-132\charts
echo Charts UI smoke on 8935, empty database, no OpenAI calls > %LOG%
start "Data Story 8935 (verify)" /min cmd /c ".venv\Scripts\python.exe -B tools\start.py --port 8935 --database tmp\verify-132\charts\data.sqlite3 --no-browser > tmp\verify-132\server-charts.log 2>&1"
".venv\Scripts\python.exe" -B tmp\verify-132\wait.py 8935
".venv\Scripts\python.exe" -B -u tools\charts_ui_smoke.py http://127.0.0.1:8935 >> %LOG% 2>&1
echo exit=%ERRORLEVEL% >> %LOG%
".venv\Scripts\python.exe" -B tools\start.py --port 8935 --database tmp\verify-132\charts\data.sqlite3 --stop >> %LOG% 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File tmp\verify-132\kill.ps1 >> %LOG% 2>&1
