@echo off
setlocal

:: Prompt the user for the migration message
set /p MIGRATION_MSG="Enter migration message (e.g., Initial_migration): "

if "%MIGRATION_MSG%"=="" (
    echo Migration message cannot be empty.
    pause
    exit /b 1
)

:: Navigate to the shared directory relative to the batch script location
cd /d "%~dp0..\..\shared"

echo.
echo ========================================================
echo Generating migration script...
echo ========================================================
..\services\authentication-service\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "%MIGRATION_MSG%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Failed to generate migration!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo Applying migration to upgrade database...
echo ========================================================
..\services\authentication-service\.venv\Scripts\python.exe -m alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Failed to upgrade database!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo Migration completed successfully!
echo ========================================================
pause
