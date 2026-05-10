@echo off
REM ============================================================
REM Hawk Eye - Windows wrapper for scripts/dev.ps1
REM ============================================================

setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1"

endlocal