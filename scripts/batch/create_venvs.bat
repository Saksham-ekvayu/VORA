@echo off
REM =====================================================
REM VORA Backend - Create Virtual Environments Script
REM =====================================================

setlocal
set "ROOT=%~dp0..\..\backend"

echo.
echo =====================================================
echo Creating Virtual Environments
echo =====================================================
echo.

python "%~dp0..\create_venvs.py"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create virtual environments.
    pause
    exit /b %errorlevel%
)

echo.
echo =====================================================
echo Virtual environments created successfully!
echo =====================================================
echo.
echo Next step: Run install_venvs.bat to install dependencies
echo.
pause
