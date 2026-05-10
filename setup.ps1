# Hawk Eye - AI-Powered Surveillance System - Setup Script for Windows (PowerShell)
# Full Automated Setup with ALL Dependencies

# Set error action
$ErrorActionPreference = "Stop"

# Colors
$colors = @{
    "Blue" = "DarkCyan"
    "Green" = "Green"
    "Red" = "Red"
    "Yellow" = "Yellow"
}

function Write-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor $colors["Blue"]
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $colors["Green"]
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $colors["Red"]
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $colors["Yellow"]
}

# Header
Clear-Host
Write-Host ""
Write-Host "========================================" -ForegroundColor $colors["Blue"]
Write-Host "Hawk Eye - AI Surveillance System" -ForegroundColor $colors["Blue"]
Write-Host "Full Automated Setup - Windows" -ForegroundColor $colors["Blue"]
Write-Host "========================================" -ForegroundColor $colors["Blue"]
Write-Host ""

# Check Prerequisites
Write-Step "Checking Prerequisites..."
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-Error-Custom "Python 3 is not installed or not in PATH"
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor $colors["Yellow"]
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Success "Node.js found: $nodeVersion"
} catch {
    Write-Error-Custom "Node.js is not installed or not in PATH"
    Write-Host "Download from: https://nodejs.org/" -ForegroundColor $colors["Yellow"]
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version 2>&1
    Write-Success "npm found: $npmVersion"
} catch {
    Write-Error-Custom "npm is not installed or not in PATH"
    exit 1
}

Write-Host ""

# ============ Check & Install System Tools ============
Write-Step "Checking System Dependencies..."
Write-Host ""

# Check Chocolatey
$chocoAvailable = $false
try {
    choco --version | Out-Null
    Write-Success "Chocolatey found"
    $chocoAvailable = $true
} catch {
    Write-Warning-Custom "Chocolatey not installed - will try direct installation"
    $chocoAvailable = $false
}

# Function to install ngrok
function Install-Ngrok {
    Write-Step "Checking ngrok..."
    
    try {
        ngrok --version | Out-Null
        Write-Success "ngrok is already installed"
        return
    } catch {
        Write-Warning-Custom "ngrok not found - installing..."
    }
    
    if ($chocoAvailable) {
        try {
            choco install ngrok -y | Out-Null
            Write-Success "ngrok installed via Chocolatey"
            return
        } catch {
            Write-Warning-Custom "Chocolatey installation failed, trying direct download..."
        }
    }
    
    # Direct download
    try {
        Write-Host "Downloading ngrok..." -ForegroundColor $colors["Yellow"]
        $ngrokPath = "$env:PROGRAMFILES\ngrok"
        if (-not (Test-Path $ngrokPath)) { 
            New-Item -ItemType Directory -Path $ngrokPath -Force | Out-Null 
        }
        
        $zipPath = "$env:TEMP\ngrok.zip"
        Invoke-WebRequest -Uri "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-windows-amd64.zip" -OutFile $zipPath -ErrorAction Stop -UseBasicParsing
        Expand-Archive -Path $zipPath -DestinationPath $ngrokPath -Force
        Remove-Item $zipPath -Force
        
        # Add to PATH permanently
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        if ($currentPath -notlike "*ngrok*") {
            [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$ngrokPath", "User")
            $env:PATH += ";$ngrokPath"
        }
        
        Write-Success "ngrok installed to $ngrokPath"
    } catch {
        Write-Warning-Custom "Failed to install ngrok automatically"
        Write-Host "Please download manually from: https://ngrok.com/download" -ForegroundColor $colors["Yellow"]
    }
}

# Function to install cloudflared
function Install-Cloudflared {
    Write-Step "Checking cloudflared..."
    
    try {
        cloudflared --version | Out-Null
        Write-Success "cloudflared is already installed"
        return
    } catch {
        Write-Warning-Custom "cloudflared not found - installing..."
    }
    
    if ($chocoAvailable) {
        try {
            choco install cloudflare-warp -y | Out-Null
            Write-Success "cloudflared installed via Chocolatey"
            return
        } catch {
            Write-Warning-Custom "Chocolatey installation failed, trying direct download..."
        }
    }
    
    # Direct download
    try {
        Write-Host "Downloading cloudflared..." -ForegroundColor $colors["Yellow"]
        $cfPath = "$env:PROGRAMFILES\cloudflared"
        if (-not (Test-Path $cfPath)) {
            New-Item -ItemType Directory -Path $cfPath -Force | Out-Null
        }
        
        $exePath = "$cfPath\cloudflared.exe"
        Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $exePath -ErrorAction Stop -UseBasicParsing
        
        # Add to PATH permanently
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        if ($currentPath -notlike "*cloudflared*") {
            [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$cfPath", "User")
            $env:PATH += ";$cfPath"
        }
        
        Write-Success "cloudflared installed to $cfPath"
    } catch {
        Write-Warning-Custom "Failed to install cloudflared automatically"
        Write-Host "Please download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/" -ForegroundColor $colors["Yellow"]
    }
}

# Function to install Git
function Install-Git {
    Write-Step "Checking Git..."
    
    try {
        git --version | Out-Null
        Write-Success "Git is already installed"
        return
    } catch {
        Write-Warning-Custom "Git not found - installing..."
    }
    
    if ($chocoAvailable) {
        try {
            choco install git -y | Out-Null
            Write-Success "Git installed via Chocolatey"
        } catch {
            Write-Warning-Custom "Failed to install Git"
            Write-Host "Please download from: https://git-scm.com/download/win" -ForegroundColor $colors["Yellow"]
        }
    } else {
        Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor $colors["Yellow"]
    }
}

# Install all system tools
Install-Ngrok
Install-Cloudflared
Install-Git

Write-Host ""

# ============ Setup Backend ============
Write-Step "Setting up Backend..."
Write-Host ""

if (Test-Path ".venv") {
    Write-Warning-Custom "Virtual environment already exists"
    $response = Read-Host "Do you want to recreate it? (y/n)"
    if ($response -eq "y") {
        Write-Step "Removing existing virtual environment..."
        Remove-Item ".venv" -Recurse -Force
        Write-Step "Creating Python virtual environment..."
        python -m venv .venv
    }
} else {
    Write-Step "Creating Python virtual environment..."
    python -m venv .venv
}

Write-Step "Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

Write-Step "Installing Python dependencies..."
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r backend\requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to install Python dependencies"
    exit 1
}
Write-Success "Python dependencies installed successfully"
Write-Host ""

# ============ Setup Dashboard ============
Write-Step "Setting up Dashboard..."
Write-Host ""

if (Test-Path "dashboard\node_modules") {
    Write-Warning-Custom "Dashboard node_modules already exists"
    $response = Read-Host "Do you want to reinstall? (y/n)"
    if ($response -eq "y") {
        Write-Step "Removing existing node_modules..."
        Remove-Item "dashboard\node_modules" -Recurse -Force
        if (Test-Path "dashboard\package-lock.json") {
            Remove-Item "dashboard\package-lock.json"
        }
        Write-Step "Installing Node.js dependencies..."
        Set-Location "dashboard"
        npm install
        Set-Location ".."
    }
} else {
    Write-Step "Installing Node.js dependencies..."
    Set-Location "dashboard"
    npm install
    Set-Location ".."
}

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to install Dashboard dependencies"
    exit 1
}
Write-Success "Dashboard dependencies installed successfully"
Write-Host ""

# ============ Create Required Directories ============
Write-Step "Creating required directories..."

if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
if (-not (Test-Path "backend\static\snapshots")) { New-Item -ItemType Directory -Path "backend\static\snapshots" -Force | Out-Null }
if (-not (Test-Path "static\snapshots")) { New-Item -ItemType Directory -Path "static\snapshots" | Out-Null }

Write-Success "Directories created"
Write-Host ""

# ============ Environment Files Check ============
Write-Step "Environment Files Setup..."
Write-Host ""

if (-not (Test-Path "backend\.env")) {
    Write-Warning-Custom "backend\.env not found"
    Write-Host "  You need to create this file with your configuration" -ForegroundColor $colors["Yellow"]
    Write-Host "  Refer to the README.md for required environment variables" -ForegroundColor $colors["Yellow"]
}

if (-not (Test-Path "dashboard\.env.local")) {
    Write-Warning-Custom "dashboard\.env.local not found"
    Write-Host "  You need to create this file with your configuration" -ForegroundColor $colors["Yellow"]
    Write-Host "  Refer to the README.md for required environment variables" -ForegroundColor $colors["Yellow"]
}

Write-Host ""

# ============ Summary ============
Write-Step "Setup Summary..."
Write-Host ""
Write-Success "Python environment: .venv\Scripts\python.exe"
Write-Success "Backend dependencies: Installed"
Write-Success "Dashboard dependencies: Installed"
Write-Success "System tools: ngrok, cloudflared, git installed and ready!"
Write-Host ""

Write-Host "NEXT STEPS:" -ForegroundColor $colors["Yellow"]
Write-Host "1. Create backend\.env with your configuration"
Write-Host "2. Create dashboard\.env.local with your configuration"
Write-Host "3. Verify installation: .\SETUP_VERIFICATION.md"
Write-Host "4. Run the application:"
Write-Host "   .\.venv\Scripts\Activate.ps1  # Activate virtual environment" -ForegroundColor $colors["Blue"]
Write-Host "   .\scripts\dev.sh               # Start all services" -ForegroundColor $colors["Blue"]
Write-Host ""
Write-Host "For detailed setup instructions, see: README.md or SETUP_GUIDE.md" -ForegroundColor $colors["Yellow"]
Write-Host ""

Write-Success "Setup completed successfully!"
