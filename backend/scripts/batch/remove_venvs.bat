@echo off
REM =====================================================
REM VORA Backend - Remove Virtual Environments Script
REM =====================================================

setlocal
set "ROOT=%~dp0..\.."

echo.
echo =====================================================
echo Removing Virtual Environments
echo =====================================================
echo.

python "%ROOT%\scripts\remove_venvs.py"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to remove virtual environments.
    pause
    exit /b %errorlevel%
)

echo.
echo =====================================================
echo Virtual environments removed successfully!
echo =====================================================
echo.
pause
