@echo off
echo ========================================================
echo Formatting Backend Code using Black and Isort...
echo ========================================================
echo.

echo [1/3] Ensuring Black and Isort are installed...
python -m pip install --upgrade black isort >nul 2>&1
if errorlevel 1 (
    echo WARNING: Could not install/upgrade black and isort. Make sure Python is in your PATH.
) else (
    echo OK.
)

:: Navigate to the backend root directory
set BACKEND_DIR=%~dp0..\..
cd /d "%BACKEND_DIR%"

echo.
echo [2/3] Running Black (Code Formatter)...
python -m black .

echo.
echo [3/3] Running Isort (Import Sorter)...
python -m isort .

echo.
echo ========================================================
echo Formatting Complete!
echo ========================================================
pause
