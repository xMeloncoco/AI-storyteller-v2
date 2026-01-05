@echo off
REM Dreamwalkers Test Environment Shutdown Script (Windows)
REM This script stops all services started by start-test.bat

setlocal enabledelayedexpansion

echo ==================================================
echo Dreamwalkers Test Environment Shutdown
echo ==================================================
echo.

echo [Stopping services...]

REM Kill Python processes running app.main
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
    set pid=%%a
    REM Check if this Python process is running our app
    wmic process where "ProcessId=!pid!" get CommandLine 2>nul | find "app.main" >nul
    if not errorlevel 1 (
        echo Stopping backend process !pid!...
        taskkill /PID !pid! /F >nul 2>&1
        echo [OK] Backend stopped
    )
)

REM Kill Node processes (npm start / electron)
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" /FO LIST ^| find "PID:"') do (
    set pid=%%a
    echo Stopping Node.js process !pid!...
    taskkill /PID !pid! /F >nul 2>&1
)

REM Kill Electron processes
tasklist /FI "IMAGENAME eq electron.exe" >nul 2>&1
if not errorlevel 1 (
    echo Stopping Electron processes...
    taskkill /IM electron.exe /F >nul 2>&1
    echo [OK] Frontend stopped
)

REM Close log viewer windows if open
taskkill /FI "WINDOWTITLE eq Backend Logs*" >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend Logs*" >nul 2>&1
taskkill /FI "WINDOWTITLE eq Dreamwalkers Backend*" >nul 2>&1
taskkill /FI "WINDOWTITLE eq Dreamwalkers Frontend*" >nul 2>&1

echo.

REM Ask about cleaning log files
set /p CLEAN_LOGS="Remove log files? (y/n, default: n): "
if /i "!CLEAN_LOGS!"=="y" (
    del /q "%~dp0backend.log" 2>nul
    del /q "%~dp0frontend.log" 2>nul
    echo [OK] Log files removed
)

echo.
echo ==================================================
echo Shutdown complete!
echo ==================================================
echo.
pause
