@echo off
REM =====================================================
REM VORA Backend - Lint Code Script
REM Uses Ruff for blazing fast code linting
REM =====================================================

echo.
echo =====================================================
echo Linting VORA Backend Code
echo =====================================================
echo.

echo [1/2] Ensuring Ruff is installed...
python -m pip install --quiet ruff 2>nul
if errorlevel 1 (
    echo WARNING: Could not install ruff. Make sure Python is in your PATH.
) else (
    echo OK.
)

REM Navigate to the backend root directory
set BACKEND_DIR=%~dp0..\..
cd /d "%BACKEND_DIR%"

echo.
echo [2/2] Running Ruff Linter...
echo Linting Python files...
python -m ruff check .
if errorlevel 1 (
    echo ERROR: Linter found issues in the code.
    pause
    exit /b 1
)
echo OK. No linting issues found!

echo.
echo =====================================================
echo Linting Complete!
echo =====================================================
echo.
pause
