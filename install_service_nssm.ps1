# =============================================================================
# MOT Nexus – Install as Windows Service using NSSM
# =============================================================================
# NSSM (Non-Sucking Service Manager) wraps any executable as a Windows Service.
# It handles auto-start on boot, crash restarts, and log rotation.
#
# PREREQUISITES:
#   1. Download NSSM from https://nssm.cc/download  (nssm-2.24.zip or later)
#   2. Extract and copy nssm.exe to C:\nssm\nssm.exe  (or any folder in PATH)
#   3. Run this script in an Administrator PowerShell:
#        cd C:\mot-nexus
#        .\install_service_nssm.ps1
# =============================================================================

#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

# ── Configuration ─────────────────────────────────────────────────────────────
$ServiceName = "MOTNexus"
$AppDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$NssmExe     = "C:\nssm\nssm.exe"        # Change if you extracted NSSM elsewhere
$UvicornExe  = "$AppDir\.venv\Scripts\uvicorn.exe"
$LogDir      = "$AppDir\logs"
$DbPath      = "$($AppDir.Replace('\','/'))/mot_nexus.db"

# ── Validate ──────────────────────────────────────────────────────────────────
if (-not (Test-Path $NssmExe)) {
    Write-Host ""
    Write-Host "ERROR: NSSM not found at $NssmExe" -ForegroundColor Red
    Write-Host ""
    Write-Host "  1. Download NSSM from: https://nssm.cc/download" -ForegroundColor Yellow
    Write-Host "  2. Extract nssm.exe (64-bit) to C:\nssm\nssm.exe" -ForegroundColor Yellow
    Write-Host "  3. Re-run this script" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $UvicornExe)) {
    Write-Host "ERROR: uvicorn.exe not found. Run setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# ── Remove existing service if present ────────────────────────────────────────
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing service '$ServiceName'..." -ForegroundColor Yellow
    & $NssmExe stop $ServiceName confirm
    & $NssmExe remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# ── Install service ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Installing Windows Service: $ServiceName" -ForegroundColor Cyan
Write-Host "  Executable : $UvicornExe" -ForegroundColor Gray
Write-Host "  App dir    : $AppDir" -ForegroundColor Gray
Write-Host "  Log dir    : $LogDir" -ForegroundColor Gray
Write-Host ""

& $NssmExe install $ServiceName $UvicornExe

# Arguments passed to uvicorn
& $NssmExe set $ServiceName AppParameters `
    "backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info --access-log"

# Working directory (PYTHONPATH needs this to resolve the backend package)
& $NssmExe set $ServiceName AppDirectory $AppDir

# Environment variables
& $NssmExe set $ServiceName AppEnvironmentExtra `
    "PYTHONPATH=$AppDir" `
    "DATABASE_URL=sqlite:///$DbPath"

# Log files (NSSM rotates these automatically)
& $NssmExe set $ServiceName AppStdout       "$LogDir\mot-nexus.log"
& $NssmExe set $ServiceName AppStderr       "$LogDir\mot-nexus-error.log"
& $NssmExe set $ServiceName AppRotateFiles  1
& $NssmExe set $ServiceName AppRotateBytes  10485760   # rotate at 10 MB

# Restart policy: restart 5 s after crash
& $NssmExe set $ServiceName AppExit Default Restart
& $NssmExe set $ServiceName AppRestartDelay 5000

# Start type: automatic (start on boot)
& $NssmExe set $ServiceName Start SERVICE_AUTO_START

# Display name shown in Services console
& $NssmExe set $ServiceName DisplayName "MOT Nexus – Resourcing Portal"
& $NssmExe set $ServiceName Description "Enterprise Resourcing Management Portal (FastAPI/uvicorn)"

# ── Start the service now ─────────────────────────────────────────────────────
Write-Host "Starting service..." -ForegroundColor Yellow
& $NssmExe start $ServiceName
Start-Sleep -Seconds 3

$svc = Get-Service -Name $ServiceName
Write-Host ""
if ($svc.Status -eq "Running") {
    Write-Host "====================================================" -ForegroundColor Green
    Write-Host "  Service '$ServiceName' is RUNNING." -ForegroundColor Green
    Write-Host "  URL  : http://localhost:8000" -ForegroundColor Green
    Write-Host "  Logs : $LogDir" -ForegroundColor Green
    Write-Host "====================================================" -ForegroundColor Green
} else {
    Write-Host "WARNING: Service status is '$($svc.Status)'." -ForegroundColor Red
    Write-Host "Check logs at: $LogDir\mot-nexus-error.log" -ForegroundColor Red
}
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor White
Write-Host "  Start   : Start-Service $ServiceName" -ForegroundColor Gray
Write-Host "  Stop    : Stop-Service  $ServiceName" -ForegroundColor Gray
Write-Host "  Restart : Restart-Service $ServiceName" -ForegroundColor Gray
Write-Host "  Status  : Get-Service $ServiceName" -ForegroundColor Gray
Write-Host "  GUI     : services.msc" -ForegroundColor Gray
