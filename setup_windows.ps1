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
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
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

# ── 2. Install uv (fast package manager) ─────────────────────────────────────
Write-Host "[2/5] Installing uv package manager..." -ForegroundColor Yellow
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "      uv already installed." -ForegroundColor Green
} else {
    try {
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        # Reload PATH so uv is available immediately
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "      uv installed." -ForegroundColor Green
    } catch {
        Write-Host "      uv install failed, falling back to pip..." -ForegroundColor Yellow
        python -m pip install uv --quiet
    }
}

# ── 3. Create virtual environment ─────────────────────────────────────────────
Write-Host "[3/5] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "      Virtual environment already exists." -ForegroundColor Green
} else {
    uv venv .venv
    Write-Host "      Virtual environment created." -ForegroundColor Green
}

# ── 4. Install Python dependencies ───────────────────────────────────────────
Write-Host "[4/5] Installing dependencies (this may take 1-2 minutes)..." -ForegroundColor Yellow
# Use the venv's own pip executable directly – this is the only guaranteed way
# to install into OUR .venv regardless of uv version or PATH quirks on Windows.
$VenvPython = "$AppDir\.venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dependency installation failed. Check the output above." -ForegroundColor Red
    exit 1
}
Write-Host "      Dependencies installed." -ForegroundColor Green

# ── 5. Create folders & seed data ────────────────────────────────────────────
Write-Host "[5/5] Initialising database..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$AppDir\logs" | Out-Null

if (Test-Path "mot_nexus.db") {
    Write-Host "      Database already exists - skipping seed." -ForegroundColor Green
} else {
    $env:PYTHONPATH = $AppDir
    # Use the full absolute path – PowerShell's & operator misreads a leading
    # ".venv\" (without .\) as a module name rather than a file path.
    & "$AppDir\.venv\Scripts\python.exe" backend\seed_data.py
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
