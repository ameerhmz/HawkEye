$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LogDir = Join-Path $RootDir "logs"
$DashboardEnvPath = Join-Path $RootDir "dashboard\.env"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

function Test-CommandExists {
    param([string]$Name)

    $null = Get-Command $Name -ErrorAction Stop
}

function Get-PythonBinary {
    $venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    return "python"
}

function Start-LoggedProcess {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$StdOutLog,
        [string]$StdErrLog
    )

    return Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdOutLog `
        -RedirectStandardError $StdErrLog `
        -PassThru
}

function Wait-ForNgrokUrl {
    param([int]$TimeoutSeconds = 30)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 2
            $tunnel = $response.tunnels | Where-Object { $_.name -eq "command_line" } | Select-Object -First 1
            if ($tunnel -and $tunnel.public_url) {
                return $tunnel.public_url
            }
        } catch {
        }

        Start-Sleep -Seconds 2
    }

    return ""
}

function Wait-ForCloudflaredUrl {
    param(
        [string]$LogFile,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $LogFile) {
            $content = Get-Content $LogFile -ErrorAction SilentlyContinue | Select-String -Pattern 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | Select-Object -Last 1
            if ($content) {
                return $content.Matches[0].Value
            }
        }

        Start-Sleep -Seconds 2
    }

    return ""
}

function Write-DashboardEnv {
    param(
        [string]$MasterUrl,
        [string]$LivekitUrl
    )

    @"
NEXT_PUBLIC_API_BASE_URL=$MasterUrl/api/backend
NEXT_PUBLIC_LIVEKIT_URL=$LivekitUrl
LIVEKIT_API_KEY=hawkeye_dev_key
LIVEKIT_API_SECRET=hawkeye_dev_secret_2026_xxxxxxxxxxxxxxxx
"@ | Set-Content -Path $DashboardEnvPath -Encoding ascii
}

function Stop-ChildProcesses {
    param([System.Diagnostics.Process[]]$Processes)

    Write-Host "Stopping services..."
    foreach ($process in $Processes) {
        if ($null -ne $process -and -not $process.HasExited) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            } catch {
            }
        }
    }
}

Test-CommandExists "npm"
Test-CommandExists "livekit-server"
Test-CommandExists "ngrok"
Test-CommandExists "cloudflared"

$PythonBin = Get-PythonBinary
$Processes = New-Object System.Collections.Generic.List[System.Diagnostics.Process]

try {
    Write-Host "Starting Tunnels..."
    $Processes.Add((Start-LoggedProcess -FilePath "ngrok" -ArgumentList @("http", "3000", "--log=stdout") -WorkingDirectory $RootDir -StdOutLog (Join-Path $LogDir "ngrok.log") -StdErrLog (Join-Path $LogDir "ngrok.err.log")))
    $Processes.Add((Start-LoggedProcess -FilePath "cloudflared" -ArgumentList @("tunnel", "--url", "http://localhost:7880", "--loglevel", "info") -WorkingDirectory $RootDir -StdOutLog (Join-Path $LogDir "cloudflared_livekit.log") -StdErrLog (Join-Path $LogDir "cloudflared_livekit.err.log")))

    Write-Host "Waiting for tunnel URLs..."
    $MasterUrl = Wait-ForNgrokUrl
    $LivekitUrl = Wait-ForCloudflaredUrl -LogFile (Join-Path $LogDir "cloudflared_livekit.log")

    if ([string]::IsNullOrWhiteSpace($MasterUrl)) {
        throw "Unable to resolve ngrok URL from local API"
    }

    if ([string]::IsNullOrWhiteSpace($LivekitUrl)) {
        throw "Unable to resolve cloudflared URL from logs"
    }

    Write-DashboardEnv -MasterUrl $MasterUrl -LivekitUrl $LivekitUrl

    Write-Host "==========================================================="
    Write-Host "LIVE URLS READY:"
    Write-Host "   Dashboard: $MasterUrl"
    Write-Host "   Camera:    $MasterUrl/camera"
    Write-Host "   LiveKit:   $LivekitUrl"
    Write-Host "==========================================================="

    Write-Host "Starting Backend (8000)..."
    $Processes.Add((Start-LoggedProcess -FilePath $PythonBin -ArgumentList @("-m", "uvicorn", "app.main:app", "--app-dir", "$RootDir\backend", "--host", "0.0.0.0", "--port", "8000") -WorkingDirectory $RootDir -StdOutLog (Join-Path $LogDir "backend.log") -StdErrLog (Join-Path $LogDir "backend.err.log")))

    Write-Host "Starting LiveKit (7880)..."
    $Processes.Add((Start-LoggedProcess -FilePath "livekit-server" -ArgumentList @("--config", (Join-Path $RootDir "livekit.yaml")) -WorkingDirectory $RootDir -StdOutLog (Join-Path $LogDir "livekit.log") -StdErrLog (Join-Path $LogDir "livekit.err.log")))

    Write-Host "Starting Dashboard (3000)..."
    $Processes.Add((Start-LoggedProcess -FilePath "npm" -ArgumentList @("run", "dev", "--", "-H", "0.0.0.0", "-p", "3000") -WorkingDirectory (Join-Path $RootDir "dashboard") -StdOutLog (Join-Path $LogDir "dashboard.log") -StdErrLog (Join-Path $LogDir "dashboard.err.log")))

    Write-Host "Starting AI Worker..."
    $workerCommand = 'set LIVEKIT_ROOM=hawkeye && "' + $PythonBin + '" worker.py'
    $Processes.Add((Start-LoggedProcess -FilePath "cmd.exe" -ArgumentList @("/c", $workerCommand) -WorkingDirectory (Join-Path $RootDir "backend") -StdOutLog (Join-Path $LogDir "worker.log") -StdErrLog (Join-Path $LogDir "worker.err.log")))

    Write-Host "Press Ctrl+C to stop all services."
    while ($true) {
        Start-Sleep -Seconds 2

        $exited = $Processes | Where-Object { $_.HasExited }
        if ($exited.Count -gt 0) {
            break
        }
    }
}
finally {
    Stop-ChildProcesses -Processes $Processes
}