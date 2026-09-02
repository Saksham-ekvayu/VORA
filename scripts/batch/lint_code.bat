@echo off
REM =====================================================
REM VORA Backend - Lint Code Script
REM Uses Ruff or Pylint based on user selection
REM =====================================================

echo.
echo =====================================================
echo Linting VORA Backend Code
echo =====================================================
echo.

echo Select the linter you want to use:
echo [A] Ruff (Blazing fast, modern standard)
echo [B] Pylint (Deep static analysis, strict)
echo.

choice /c AB /n /m "Enter your choice (A/B): "
if errorlevel 2 goto run_pylint
if errorlevel 1 goto run_ruff

:run_ruff
echo.
echo [1/2] Ensuring Ruff is installed...
python -m pip install --quiet ruff 2>nul
if errorlevel 1 (
    echo WARNING: Could not install ruff. Make sure Python is in your PATH.
) else (
    echo OK.
)

REM Navigate to the backend root directory
set BACKEND_DIR=%~dp0..\..\backend
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
goto end

:run_pylint
echo.
echo [1/2] Ensuring Pylint is installed...
python -m pip install --quiet pylint 2>nul
if errorlevel 1 (
    echo WARNING: Could not install pylint. Make sure Python is in your PATH.
) else (
    echo OK.
)

REM Navigate to the backend root directory
set BACKEND_DIR=%~dp0..\..\backend
cd /d "%BACKEND_DIR%"

echo.
echo [2/2] Running Pylint...
echo Linting Python files...
REM Run Pylint on backend directories (ignoring virtual envs and using all CPU cores)
python -m pylint services shared gateway --ignore=.venv,__pycache__ -j 0
if errorlevel 1 (
    echo ERROR: Linter found issues in the code.
    pause
    exit /b 1
)
echo OK. No linting issues found!
goto end

:end
echo.
echo =====================================================
echo Linting Complete!
echo =====================================================
echo.
pause
