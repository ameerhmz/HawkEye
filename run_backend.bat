@echo off
REM ============================================================
REM CCTV Backend - Windows Startup Script
REM ============================================================

setlocal enabledelayedexpansion

title CCTV Backend (FastAPI + AI Worker)

if not exist ".venv" (
    echo.
    echo [ERROR] Virtual environment not found
    echo Please run setup.bat first
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo.
echo ============================================================
echo CCTV Backend Starting...
echo ============================================================
echo.
echo API: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop
echo.

set PYTHONUNBUFFERED=1
set PYTHONPATH=%CD%\backend

REM Start backend in current terminal
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
