# =============================================================================
# MOT Nexus – One-Time Windows Setup Script
# =============================================================================
# Run once on the server as Administrator:
#   Right-click PowerShell → "Run as Administrator"
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser   (first time only)
#   cd C:\mot-nexus
#   .\setup_windows.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $AppDir

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  MOT Nexus - Windows Setup" -ForegroundColor Cyan
Write-Host "  App directory: $AppDir" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Python ──────────────────────────────────────────────────────────
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pyVersion = & python --version 2>&1
    Write-Host "      Found: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "ERROR: Python not found." -ForegroundColor Red
    Write-Host "  Download Python 3.11+ from: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  IMPORTANT: During install, check 'Add Python to PATH'" -ForegroundColor Red
    exit 1
}

# ── 2. Create virtual environment ─────────────────────────────────────────────
# Use the standard 'python -m venv' which always includes pip.
# (uv venv intentionally omits pip, causing 'No module named pip' errors.)
Write-Host "[2/4] Creating virtual environment..." -ForegroundColor Yellow
$VenvPython = "$AppDir\.venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    Write-Host "      Virtual environment already exists." -ForegroundColor Green
} else {
    & python -m venv "$AppDir\.venv"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "      Virtual environment created." -ForegroundColor Green
}

# ── 3. Install Python dependencies ───────────────────────────────────────────
# Run pip from INSIDE the venv – guarantees packages land in the right place.
Write-Host "[3/4] Installing dependencies (this may take 2-3 minutes)..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip upgrade failed." -ForegroundColor Red
    exit 1
}
& $VenvPython -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dependency installation failed. Check the output above." -ForegroundColor Red
    exit 1
}
Write-Host "      Dependencies installed." -ForegroundColor Green

# ── 4. Create folders & seed data ────────────────────────────────────────────
Write-Host "[4/4] Initialising database..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$AppDir\logs" | Out-Null

if (Test-Path "mot_nexus.db") {
    Write-Host "      Database already exists - skipping seed." -ForegroundColor Green
} else {
    $env:PYTHONPATH = $AppDir
    # Full absolute path avoids PowerShell misreading '.venv\' as a module name.
    & $VenvPython backend\seed_data.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Database seeding failed. Check the output above." -ForegroundColor Red
        exit 1
    }
    Write-Host "      Database seeded with sample data." -ForegroundColor Green
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  To start the application run:" -ForegroundColor White
Write-Host "    .\start_prod.bat          (Command Prompt)" -ForegroundColor White
Write-Host "    .\start_prod.ps1          (PowerShell)" -ForegroundColor White
Write-Host ""
Write-Host "  To install as a Windows Service (auto-start on boot):" -ForegroundColor White
Write-Host "    .\install_service_nssm.ps1" -ForegroundColor White
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
