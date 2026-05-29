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

# Full absolute paths to venv executables – avoids PowerShell misreading
# ".venv\..." as a module name instead of a file path.
$PythonExe  = "$AppDir\.venv\Scripts\python.exe"
$UvicornExe = "$AppDir\.venv\Scripts\uvicorn.exe"

# Check venv
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Virtual environment not found at $AppDir\.venv" -ForegroundColor Red
    Write-Host "       Run .\setup_windows.ps1 first, then retry." -ForegroundColor Red
    exit 1
}

# Seed DB if missing – use explicit venv Python path
if (-not (Test-Path "mot_nexus.db")) {
    Write-Host "No database found - seeding sample data..." -ForegroundColor Yellow
    & $PythonExe backend\seed_data.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Seeding failed. Check the output above." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

Write-Host "Server starting on http://0.0.0.0:8000  (Press Ctrl+C to stop)" -ForegroundColor Green
Write-Host ""

# Prefer uvicorn.exe; fall back to 'python -m uvicorn' if the exe is missing.
# Note: --workers 1 is intentional on Windows + SQLite.
# FastAPI is async; a single worker handles many concurrent requests efficiently.
if (Test-Path $UvicornExe) {
    & $UvicornExe backend.app.main:app `
        --host 0.0.0.0 `
        --port 8000 `
        --workers 1 `
        --log-level info `
        --access-log
} else {
    & $PythonExe -m uvicorn backend.app.main:app `
        --host 0.0.0.0 `
        --port 8000 `
        --workers 1 `
        --log-level info `
        --access-log
}
