#!/usr/bin/env bash
# ====================================================================
#  Multimodal Attendance & Engagement Agent - Linux/macOS Startup
# ====================================================================

set -e

if [ -f ".venv/bin/python" ]; then
    PYTHON_EXE=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON_EXE="venv/bin/python"
else
    PYTHON_EXE="python3"
fi

echo "[1/2] Initializing SQLite database and schema..."
$PYTHON_EXE -c "from app import create_app; create_app('development')"

echo "[2/2] Launching Multimodal Agent on http://127.0.0.1:5000..."
$PYTHON_EXE run.py
