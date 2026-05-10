@echo off
REM ============================================================
REM CCTV Dashboard - Windows Startup Script
REM ============================================================

setlocal enabledelayedexpansion

title CCTV Dashboard (Next.js)

if not exist "dashboard\package.json" (
    echo.
    echo [ERROR] Dashboard not found
    echo.
    pause
    exit /b 1
)

if not exist "dashboard\node_modules" (
    echo.
    echo [WARNING] Node.js dependencies not installed
    echo Installing now...
    echo.
    cd dashboard
    call npm install
    cd ..
)

echo.
echo ============================================================
echo CCTV Dashboard Starting...
echo ============================================================
echo.
echo Dashboard: http://localhost:3000
echo.
echo Press Ctrl+C to stop
echo.

cd dashboard
call npm run dev

pause
