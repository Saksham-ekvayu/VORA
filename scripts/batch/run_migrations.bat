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
cd /d "%~dp0..\..\backend\shared"

:: Auto-heal: Ensure versions directory exists
if not exist "alembic\versions" mkdir "alembic\versions"

:: Auto-heal: Check if the versions folder has any Python files. 
:: If it is empty, the user deleted all migrations. We must drop the alembic_version table to prevent the "Can't locate revision" crash.
dir /A-D /B "alembic\versions\*.py" >nul 2>&1
if errorlevel 1 (
    echo [INFO] No existing migrations found. Resetting database migration state to start fresh...
    ..\services\authentication-service\.venv\Scripts\python.exe alembic\reset_alembic.py
)

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
