@echo off
REM ====================================================================
REM  Multimodal Attendance & Engagement Agent - Windows Local Startup
REM ====================================================================

echo [1/3] Checking environment...
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [2/3] Verifying database and local tables...
%PYTHON_EXE% -c "from app import create_app; create_app('development')"

echo [3/3] Starting Offline Multimodal Agent Server...
echo --------------------------------------------------------------------
echo Web UI will be available at: http://127.0.0.1:5000
echo Default Instructor Login: instructor / admin123
echo --------------------------------------------------------------------
%PYTHON_EXE% run.py
pause
