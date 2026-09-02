@echo off
REM =====================================================
REM VORA Backend - Run All Services Script
REM Ports are dynamically extracted from .env files
REM =====================================================

setlocal enabledelayedexpansion

REM Calculate the ROOT directory (go up 2 levels from batch file location: scripts\batch -> root, then to backend)
pushd "%~dp0..\..\backend"
set "ROOT=%cd%"
popd

REM Check if virtual environments exist
echo Checking if virtual environments are set up...
if not exist "%ROOT%\gateway\.venv" (
    echo ERROR: Virtual environments not found. Please run install_venvs.bat first.
    pause
    exit /b 1
)

REM Extract ports from .env files
set P_AUTH=7001
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\authentication-service\.env" 2^>nul') do set P_AUTH=%%a

set P_PROF=7002
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\profile-service\.env" 2^>nul') do set P_PROF=%%a

set P_DASH=7003
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\dashboard-service\.env" 2^>nul') do set P_DASH=%%a

set P_FCAT=7004
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\framework-category-service\.env" 2^>nul') do set P_FCAT=%%a

set P_FW=7005
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\framework-service\.env" 2^>nul') do set P_FW=%%a

set P_DFW=7006
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\deployment-framework-service\.env" 2^>nul') do set P_DFW=%%a

set P_EXT=7007
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\extract-controls-service\.env" 2^>nul') do set P_EXT=%%a

set P_COMP=7008
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\compliance-agent-service\.env" 2^>nul') do set P_COMP=%%a

set P_AI=7009
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\ai-analysis-service\.env" 2^>nul') do set P_AI=%%a

set P_MCP=7010
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\services\mcp-boto3-server\.env" 2^>nul') do set P_MCP=%%a

set P_GW=8000
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" "%ROOT%\gateway\.env" 2^>nul') do set P_GW=%%a

REM Check if Windows Terminal is available
where wt >nul 2>&1
if errorlevel 1 (
    echo.
    echo Windows Terminal not found. Opening services in separate CMD windows...
    echo.
    start "authentication-service (!P_AUTH!)" cmd /k "cd /d "%ROOT%\services\authentication-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_AUTH! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "profile-service (!P_PROF!)" cmd /k "cd /d "%ROOT%\services\profile-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_PROF! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "dashboard-service (!P_DASH!)" cmd /k "cd /d "%ROOT%\services\dashboard-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_DASH! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "framework-category-service (!P_FCAT!)" cmd /k "cd /d "%ROOT%\services\framework-category-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_FCAT! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "framework-service (!P_FW!)" cmd /k "cd /d "%ROOT%\services\framework-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_FW! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "deployment-framework-service (!P_DFW!)" cmd /k "cd /d "%ROOT%\services\deployment-framework-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_DFW! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "extract-controls-service (!P_EXT!)" cmd /k "cd /d "%ROOT%\services\extract-controls-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_EXT! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "compliance-agent-service (!P_COMP!)" cmd /k "cd /d "%ROOT%\services\compliance-agent-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_COMP! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "ai-analysis-service (!P_AI!)" cmd /k "cd /d "%ROOT%\services\ai-analysis-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_AI! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "mcp-boto3-server (!P_MCP!)" cmd /k "cd /d "%ROOT%\services\mcp-boto3-server" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_MCP! --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "api-gateway (!P_GW!)" cmd /k "cd /d "%ROOT%\gateway" && .venv\Scripts\activate.bat && python -m uvicorn main:app --host localhost --port !P_GW! --reload"
    timeout /t 1 /nobreak
    start "frontend (Vite)" cmd /k "cd /d "%ROOT%\..\frontend" && pnpm dev"
    echo.
    echo All services started in separate windows.
    echo Press any key to exit...
    pause >nul
    exit /b
)

REM Open Windows Terminal with tabs for each service
echo Opening Windows Terminal with all services...
echo.

wt -w new ^
    new-tab --title "authentication-service (!P_AUTH!)" -d "%ROOT%\services\authentication-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_AUTH! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "profile-service (!P_PROF!)" -d "%ROOT%\services\profile-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_PROF! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "dashboard-service (!P_DASH!)" -d "%ROOT%\services\dashboard-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_DASH! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "framework-category-service (!P_FCAT!)" -d "%ROOT%\services\framework-category-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_FCAT! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "framework-service (!P_FW!)" -d "%ROOT%\services\framework-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_FW! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "deployment-framework-service (!P_DFW!)" -d "%ROOT%\services\deployment-framework-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_DFW! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "extract-controls-service (!P_EXT!)" -d "%ROOT%\services\extract-controls-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_EXT! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "compliance-agent-service (!P_COMP!)" -d "%ROOT%\services\compliance-agent-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_COMP! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "ai-analysis-service (!P_AI!)" -d "%ROOT%\services\ai-analysis-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_AI! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "mcp-boto3-server (!P_MCP!)" -d "%ROOT%\services\mcp-boto3-server" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port !P_MCP! --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "api-gateway (!P_GW!)" -d "%ROOT%\gateway" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn main:app --host localhost --port !P_GW! --reload" ^
    ; new-tab --title "frontend (Vite)" -d "%ROOT%\..\frontend" cmd /k "pnpm dev"

echo.
echo Windows Terminal opened with all services running in tabs.
