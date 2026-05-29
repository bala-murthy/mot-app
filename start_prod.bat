@echo off
:: =============================================================================
:: MOT Nexus – Production Start Script (Windows Command Prompt)
:: Double-click this file or run from Command Prompt to start the server.
:: =============================================================================

setlocal enabledelayedexpansion

:: Resolve the directory containing this script
set "APP_DIR=%~dp0"
:: Remove trailing backslash
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

cd /d "%APP_DIR%"

:: Set environment
set "PYTHONPATH=%APP_DIR%"
set "DATABASE_URL=sqlite:///%APP_DIR:\=/%/mot_nexus.db"

echo.
echo ====================================================
echo   MOT Nexus - Enterprise Resourcing Portal
echo   Starting in PRODUCTION mode
echo   App dir : %APP_DIR%
echo   Port    : 8000
echo   URL     : http://localhost:8000
echo ====================================================
echo.

:: Check virtual environment exists
if not exist "%APP_DIR%\.venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Run setup_windows.ps1 first.
    pause
    exit /b 1
)

:: Seed database if missing
if not exist "%APP_DIR%\mot_nexus.db" (
    echo No database found - seeding sample data...
    "%APP_DIR%\.venv\Scripts\python.exe" backend\seed_data.py
    echo.
)

echo Server starting... Press Ctrl+C to stop.
echo.

:: Start uvicorn
:: Note: --workers 1 is correct for Windows + SQLite.
::       FastAPI is async so a single worker handles many concurrent requests.
"%APP_DIR%\.venv\Scripts\uvicorn.exe" backend.app.main:app ^
    --host 0.0.0.0 ^
    --port 8000 ^
    --workers 1 ^
    --log-level info ^
    --access-log

pause
