@echo off
REM =====================================================
REM VORA Backend - Install Virtual Environments Script
REM =====================================================

setlocal enabledelayedexpansion

REM Calculate the ROOT directory
pushd "%~dp0..\\.."
set "ROOT=%cd%"
popd

echo.
echo =====================================================
echo Installing VORA Backend Virtual Environments
echo =====================================================
echo.

REM Check if shared directory exists
if not exist "%ROOT%\shared" (
    echo WARNING: Shared directory not found at %ROOT%\shared
    echo Skipping shared package installation.
) else (
    echo [1/3] Installing shared package...
    cd /d "%ROOT%\shared"
    python -m pip install -e .
    if errorlevel 1 (
        echo ERROR: Failed to install shared package.
        pause
        exit /b 1
    )
    echo OK.
)

echo.
echo [2/3] Creating virtual environments for all services...
cd /d "%ROOT%"
python scripts\create_venvs.py
if errorlevel 1 (
    echo ERROR: Failed to create virtual environments.
    pause
    exit /b 1
)
echo OK.

echo.
echo [3/3] Installing dependencies in each service...
echo.

REM Check if Windows Terminal is available
where wt >nul 2>&1
if errorlevel 1 (
    echo Windows Terminal not found. Installing dependencies sequentially...
    echo.
    
    cd /d "%ROOT%\services\authentication-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing authentication-service dependencies.
    
    cd /d "%ROOT%\services\profile-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing profile-service dependencies.
    
    cd /d "%ROOT%\services\dashboard-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing dashboard-service dependencies.
    
    cd /d "%ROOT%\services\framework-category-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing framework-category-service dependencies.
    
    cd /d "%ROOT%\services\framework-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing framework-service dependencies.
    
    cd /d "%ROOT%\services\deployment-framework-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing deployment-framework-service dependencies.
    
    cd /d "%ROOT%\services\extract-controls-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing extract-controls-service dependencies.

    cd /d "%ROOT%\services\compliance-agent-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing compliance-agent-service dependencies.

    cd /d "%ROOT%\services\ai-analysis-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing ai-analysis-service dependencies.
    
    cd /d "%ROOT%\gateway"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    if errorlevel 1 echo ERROR installing gateway dependencies.
    
    echo.
    echo =====================================================
    echo All services installed successfully!
    echo =====================================================
    echo.
    echo Next steps:
    echo 1. Run run_services.bat to start all services
    echo 2. Access the API Gateway at: http://localhost:8000
    echo.
    pause
    exit /b
)

REM Open Windows Terminal with tabs for each service to install dependencies
echo Opening Windows Terminal with installation tabs...
echo.

wt -w new ^
    new-tab --title "authentication-service" -d "%ROOT%\services\authentication-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "profile-service" -d "%ROOT%\services\profile-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "dashboard-service" -d "%ROOT%\services\dashboard-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "framework-category-service" -d "%ROOT%\services\framework-category-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "framework-service" -d "%ROOT%\services\framework-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "deployment-framework-service" -d "%ROOT%\services\deployment-framework-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "extract-controls-service" -d "%ROOT%\services\extract-controls-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "compliance-agent-service" -d "%ROOT%\services\compliance-agent-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "ai-analysis-service" -d "%ROOT%\services\ai-analysis-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "api-gateway" -d "%ROOT%\gateway" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause"

echo.
echo =====================================================
echo Installation complete! Check Windows Terminal tabs.
echo =====================================================
echo.
