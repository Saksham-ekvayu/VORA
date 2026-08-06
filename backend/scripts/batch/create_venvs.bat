@echo off
REM =====================================================
REM VORA Backend - Create Virtual Environments Script
REM =====================================================

setlocal
set "ROOT=%~dp0..\.."

echo.
echo =====================================================
echo Creating Virtual Environments
echo =====================================================
echo.

python "%ROOT%\scripts\create_venvs.py" --install

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
