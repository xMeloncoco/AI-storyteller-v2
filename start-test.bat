@echo off
REM Dreamwalkers Test Environment Startup Script (Windows)
REM This script starts both backend and frontend services for testing

setlocal enabledelayedexpansion

echo ==================================================
echo Dreamwalkers Test Environment Startup
echo ==================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"
set "PID_FILE=%SCRIPT_DIR%.test-pids"

REM Check prerequisites
echo [Checking prerequisites...]
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from https://www.python.org
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 18 or higher from https://nodejs.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i

echo [OK] Python found: %PYTHON_VERSION%
echo [OK] Node.js found: %NODE_VERSION%
echo.

REM Setup Python virtual environment
echo [Setting up Python environment...]
cd /d "%BACKEND_DIR%"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

REM Check if dependencies need to be installed
if not exist "venv\.deps_installed" (
    echo Installing Python dependencies...
    pip install -q -r requirements.txt
    type nul > venv\.deps_installed
) else (
    REM Check if requirements.txt is newer
    for %%F in (requirements.txt) do set REQ_TIME=%%~tF
    for %%F in (venv\.deps_installed) do set DEPS_TIME=%%~tF
    REM Simple check - just reinstall if file is missing marker
)

echo [OK] Python environment ready
echo.

REM Check for .env file
if not exist "%BACKEND_DIR%\.env" (
    echo [WARNING] .env file not found in backend directory
    echo Creating .env from .env.example...
    if exist "%BACKEND_DIR%\.env.example" (
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
        echo [WARNING] Please edit backend\.env with your AI provider settings
    ) else (
        echo [ERROR] .env.example not found
        pause
        exit /b 1
    )
)
echo.

REM Setup Frontend
echo [Setting up Frontend environment...]
cd /d "%FRONTEND_DIR%"

if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

echo [OK] Frontend environment ready
echo.

REM Start Backend
echo [Starting backend server...]
cd /d "%BACKEND_DIR%"
call venv\Scripts\activate.bat

REM Start backend in new window
start "Dreamwalkers Backend" /min cmd /c "python -m app.main > ..\backend.log 2>&1"

echo [OK] Backend starting...
echo   Logs: backend.log
echo.

REM Wait for backend to be ready
echo [Waiting for backend to be ready...]
set /a attempts=0
:wait_backend
set /a attempts+=1
if %attempts% gtr 30 (
    echo [ERROR] Backend failed to start. Check backend.log
    pause
    exit /b 1
)

REM Try to connect to backend
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_backend
)

echo [OK] Backend is ready
echo.

REM Ask about test data
set /p LOAD_DATA="Load test data? (y/n, default: y): "
if "!LOAD_DATA!"=="" set LOAD_DATA=y

if /i "!LOAD_DATA!"=="y" (
    echo [Loading test data...]
    cd /d "%BACKEND_DIR%"
    call venv\Scripts\activate.bat
    python load_test_data.py
    echo [OK] Test data loaded
    echo.
)

REM Start Frontend
echo [Starting frontend application...]
cd /d "%FRONTEND_DIR%"

REM Start frontend in new window
start "Dreamwalkers Frontend" /min cmd /c "npm start > ..\frontend.log 2>&1"

echo [OK] Frontend starting...
echo   Logs: frontend.log
echo.

echo ==================================================
echo Test Environment Ready!
echo ==================================================
echo.
echo Services:
echo   Backend:  http://localhost:8000
echo   Frontend: Desktop application should open automatically
echo.
echo Logs:
echo   Backend:  backend.log
echo   Frontend: frontend.log
echo.
echo To stop:
echo   Run stop-test.bat or close the backend/frontend windows
echo.
echo Press any key to open log viewer...
pause >nul

REM Open log viewer
start "Backend Logs" powershell -Command "Get-Content -Path '%SCRIPT_DIR%backend.log' -Wait -Tail 20"
start "Frontend Logs" powershell -Command "Get-Content -Path '%SCRIPT_DIR%frontend.log' -Wait -Tail 20"

echo.
echo Log viewers opened in separate windows
echo You can close this window - services will continue running
echo.
pause
