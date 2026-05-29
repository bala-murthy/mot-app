# =============================================================================
# MOT Nexus – Production Start Script (PowerShell)
# Run from PowerShell: .\start_prod.ps1
# =============================================================================

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $AppDir

# Set environment variables
$env:PYTHONPATH   = $AppDir
$env:DATABASE_URL = "sqlite:///$($AppDir.Replace('\','/') )/mot_nexus.db"

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  MOT Nexus - Enterprise Resourcing Portal" -ForegroundColor Cyan
Write-Host "  Mode    : PRODUCTION" -ForegroundColor Cyan
Write-Host "  App dir : $AppDir" -ForegroundColor Cyan
Write-Host "  Port    : 8000" -ForegroundColor Cyan
Write-Host "  URL     : http://localhost:8000" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Check venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found. Run setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}

# Seed DB if missing
if (-not (Test-Path "mot_nexus.db")) {
    Write-Host "No database found - seeding sample data..." -ForegroundColor Yellow
    & .venv\Scripts\python.exe backend\seed_data.py
    Write-Host ""
}

Write-Host "Server starting on http://0.0.0.0:8000  (Press Ctrl+C to stop)" -ForegroundColor Green
Write-Host ""

# Note: --workers 1 is intentional on Windows + SQLite.
# FastAPI is async; a single worker handles many concurrent requests efficiently.
& .venv\Scripts\uvicorn.exe backend.app.main:app `
    --host 0.0.0.0 `
    --port 8000 `
    --workers 1 `
    --log-level info `
    --access-log
