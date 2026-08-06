@echo off
setlocal enabledelayedexpansion

REM Calculate the ROOT directory
pushd "%~dp0..\\.."
set "ROOT=%cd%"
popd

echo Installing shared package...
cd /d "%ROOT%\shared"
pip install -e .
if errorlevel 1 exit /b %errorlevel%

echo.
echo Creating virtual environments for all services...
cd /d "%ROOT%"
python scripts\create_venvs.py

echo Installing dependencies in each service...

REM Check if Windows Terminal is available
where wt >nul 2>&1
if errorlevel 1 (
    echo Windows Terminal not found. Installing dependencies sequentially...
    
    cd /d "%ROOT%\services\authentication-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    cd /d "%ROOT%\services\profile-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    cd /d "%ROOT%\services\dashboard-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    cd /d "%ROOT%\services\framework-category-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    cd /d "%ROOT%\services\framework-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    cd /d "%ROOT%\services\deployment-framework-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    cd /d "%ROOT%\services\comparison-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt

    cd /d "%ROOT%\services\compliance-agent-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt

    cd /d "%ROOT%\services\deployment-gap-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt

    cd /d "%ROOT%\services\extract-controls-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt

    cd /d "%ROOT%\services\load-document-service"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    cd /d "%ROOT%\gateway"
    call .venv\Scripts\activate.bat && pip install -r requirements.txt
    
    echo All services installed successfully!
    pause
    exit /b
)

REM Open Windows Terminal with tabs for each service to install dependencies
wt -w new new-tab --title "authentication-service" -d "%ROOT%\services\authentication-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "profile-service" -d "%ROOT%\services\profile-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "dashboard-service" -d "%ROOT%\services\dashboard-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "framework-category-service" -d "%ROOT%\services\framework-category-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "framework-service" -d "%ROOT%\services\framework-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "deployment-framework-service" -d "%ROOT%\services\deployment-framework-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "comparison-service" -d "%ROOT%\services\comparison-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "compliance-agent-service" -d "%ROOT%\services\compliance-agent-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "deployment-gap-service" -d "%ROOT%\services\deployment-gap-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "extract-controls-service" -d "%ROOT%\services\extract-controls-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "load-document-service" -d "%ROOT%\services\load-document-service" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause" ^
    ; new-tab --title "api-gateway" -d "%ROOT%\gateway" cmd /k ".venv\Scripts\activate.bat && pip install -r requirements.txt && pause"

echo.
echo Opening Windows Terminal with installation tabs for all services...
pause

