@echo off
REM Hawk Eye - AI-Powered Surveillance System - Setup Script for Windows
REM This script automates the complete setup for Windows with ALL dependencies

setlocal enabledelayedexpansion
cd /d "%~dp0"

cls

echo.
echo ========================================
echo Hawk Eye - AI Surveillance System
echo Full Automated Setup - Windows
echo ========================================
echo.

REM ============ Check Prerequisites ============
echo [*] Checking Prerequisites...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python 3 is not installed or not in PATH
    echo     Download from: https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during installation
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%

node --version >nul 2>&1
if errorlevel 1 (
    echo [X] Node.js is not installed or not in PATH
    echo     Download from: https://nodejs.org/
    echo     Make sure to add Node.js to PATH during installation
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js found: %NODE_VERSION%

npm --version >nul 2>&1
if errorlevel 1 (
    echo [X] npm is not installed or not in PATH
    exit /b 1
)
for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo [OK] npm found: %NPM_VERSION%

echo.

REM ============ Check & Install System Tools ============
echo [*] Checking System Dependencies...
echo.

REM Check Chocolatey
choco --version >nul 2>&1
if errorlevel 1 (
    echo [!] Chocolatey not installed - will try direct installation for tools
    set CHOCO_AVAILABLE=0
) else (
    echo [OK] Chocolatey found
    set CHOCO_AVAILABLE=1
)

REM Install ngrok
echo [*] Checking ngrok...
ngrok --version >nul 2>&1
if errorlevel 1 (
    echo [!] ngrok not found - installing...
    if !CHOCO_AVAILABLE! equ 1 (
        choco install ngrok -y
    ) else (
        echo [*] Download ngrok from: https://ngrok.com/download
        echo [*] Extract and add to PATH, then run this script again
        REM Alternative: download via PowerShell
        powershell -Command "Invoke-WebRequest -Uri 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-windows-amd64.zip' -OutFile 'ngrok.zip'; Expand-Archive -Path 'ngrok.zip' -DestinationPath '%PROGRAMFILES%\ngrok'; Remove-Item 'ngrok.zip'" 2>nul
        setx PATH "%PATH%;%PROGRAMFILES%\ngrok"
        echo [OK] ngrok installed to %PROGRAMFILES%\ngrok
    )
)
if not errorlevel 1 (
    echo [OK] ngrok available
)

REM Install cloudflared
echo [*] Checking cloudflared...
cloudflared --version >nul 2>&1
if errorlevel 1 (
    echo [!] cloudflared not found - installing...
    if !CHOCO_AVAILABLE! equ 1 (
        choco install cloudflare-warp -y
    ) else (
        echo [*] Download cloudflared from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
        echo [*] Or use: https://github.com/cloudflare/cloudflared/releases
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%PROGRAMFILES%\cloudflared.exe'" 2>nul
        setx PATH "%PATH%;%PROGRAMFILES%"
        echo [OK] cloudflared installed to %PROGRAMFILES%
    )
)
if not errorlevel 1 (
    echo [OK] cloudflared available
)

REM Install Git (if not present)
echo [*] Checking Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [!] Git not found - installing...
    if !CHOCO_AVAILABLE! equ 1 (
        choco install git -y
    ) else (
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/latest/download/Git-2.44.0-64-bit.exe' -OutFile 'GitInstaller.exe'; Start-Process -FilePath 'GitInstaller.exe' -Wait; Remove-Item 'GitInstaller.exe'" 2>nul
    )
) else (
    echo [OK] Git found
)

echo.


REM ============ Setup Backend ============
echo [*] Setting up Backend...
echo.

if exist ".venv" (
    echo [!] Virtual environment already exists
    set /p RECREATE="Do you want to recreate it? (y/n): "
    if /i "!RECREATE!"=="y" (
        echo [*] Removing existing virtual environment...
        rmdir /s /q .venv
        echo [*] Creating Python virtual environment...
        python -m venv .venv
    )
) else (
    echo [*] Creating Python virtual environment...
    python -m venv .venv
)

echo [*] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [*] Installing Python dependencies...
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r backend\requirements.txt

if errorlevel 1 (
    echo [X] Failed to install Python dependencies
    exit /b 1
)
echo [OK] Python dependencies installed successfully
echo.

REM ============ Setup Dashboard ============
echo [*] Setting up Dashboard...
echo.

if exist "dashboard\node_modules" (
    echo [!] Dashboard node_modules already exists
    set /p REINSTALL="Do you want to reinstall? (y/n): "
    if /i "!REINSTALL!"=="y" (
        echo [*] Removing existing node_modules...
        rmdir /s /q dashboard\node_modules
        if exist "dashboard\package-lock.json" del dashboard\package-lock.json
        echo [*] Installing Node.js dependencies...
        cd dashboard
        call npm install
        cd ..
    )
) else (
    echo [*] Installing Node.js dependencies...
    cd dashboard
    call npm install
    cd ..
)

if errorlevel 1 (
    echo [X] Failed to install Dashboard dependencies
    exit /b 1
)
echo [OK] Dashboard dependencies installed successfully
echo.

REM ============ Create Required Directories ============
echo [*] Creating required directories...
if not exist "logs" mkdir logs
if not exist "backend\static\snapshots" mkdir backend\static\snapshots
if not exist "static\snapshots" mkdir static\snapshots
echo [OK] Directories created
echo.

REM ============ Environment Files Check ============
echo [*] Environment Files Setup...
echo.
if not exist "backend\.env" (
    echo [!] backend\.env not found
    echo     You need to create this file with your configuration
    echo     Refer to the README.md for required environment variables
)

if not exist "dashboard\.env.local" (
    echo [!] dashboard\.env.local not found
    echo     You need to create this file with your configuration
    echo     Refer to the README.md for required environment variables
)

echo.

REM ============ Summary ============
echo [*] Setup Summary...
echo.
echo [OK] Python environment: .venv\Scripts\python.exe
echo [OK] Backend dependencies: Installed
echo [OK] Dashboard dependencies: Installed
echo [OK] System tools: Installed (ngrok, cloudflared, git)
echo.

echo NEXT STEPS:
echo 1. Create backend\.env with your configuration
echo 2. Create dashboard\.env.local with your configuration
echo 3. Run the application:
echo    .venv\Scripts\activate.bat    [Activate virtual environment]
echo    .\scripts\dev.sh               [Start all services]
echo.
echo For detailed setup instructions, see: README.md
echo.
echo [OK] Setup completed successfully!
echo.

pause

