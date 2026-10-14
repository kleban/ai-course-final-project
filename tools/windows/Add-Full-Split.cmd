@echo off
chcp 65001 >nul
title Data Story - Seoul split with all fields
cd /d "%~dp0\..\.."
echo Seoul: split with all 11 fields + model. Stop the service first (Stop.cmd).
if exist tmp\split-146-test rd /s /q tmp\split-146-test
robocopy runtime tmp\split-146-test /E /XD dependencies /XF *.lock /NFL /NDL /NJH /NJS >nul
".venv\Scripts\python.exe" -B -u tools\run_steps.py split-146-test "Test on a copy::.venv\Scripts\python.exe -B tools\add_full_split.py --database tmp\split-146-test\data-story.sqlite3 --out tmp\split-146-test.json"
if errorlevel 1 (
  echo Test failed - runtime NOT changed. Log: tmp\split-146-test.log
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -B -u tools\run_steps.py split-146 "Working base::.venv\Scripts\python.exe -B tools\add_full_split.py"
pause
