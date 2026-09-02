@echo off
REM =====================================================
REM VORA Backend - Format Code Script
REM Uses Black for code formatting and Isort for imports
REM =====================================================

echo.
echo =====================================================
echo Formatting VORA Backend Code
echo =====================================================
echo.

echo [1/3] Ensuring Black and Isort are installed...
python -m pip install --quiet black isort 2>nul
if errorlevel 1 (
    echo WARNING: Could not install black and isort. Make sure Python is in your PATH.
) else (
    echo OK.
)

REM Navigate to the backend root directory
set BACKEND_DIR=%~dp0..\..\backend
cd /d "%BACKEND_DIR%"

echo.
echo [2/3] Running Black (Code Formatter)...
echo Formatting Python files...
python -m black . --extend-exclude "\.venv|__pycache__|\.ipynb"
if errorlevel 1 (
    echo ERROR: Black formatting failed.
    pause
    exit /b 1
)
echo OK.

echo.
echo [3/3] Running Isort (Import Sorter)...
echo Sorting imports in Python files...
python -m isort . --skip-gitignore --skip ".venv"
if errorlevel 1 (
    echo ERROR: Isort formatting failed.
    pause
    exit /b 1
)
echo OK.

echo.
echo =====================================================
echo Formatting Complete!
echo =====================================================
echo.
echo All Python files in backend have been formatted.
echo.
pause
