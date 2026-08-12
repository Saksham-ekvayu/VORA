@echo off
REM =====================================================
REM VORA Backend - Run All Services Script
REM Services are configured with ports:
REM   - authentication-service: 7001
REM   - profile-service: 7002
REM   - dashboard-service: 7003
REM   - framework-category-service: 7004
REM   - framework-service: 7005
REM   - deployment-framework-service: 7006
REM   - extract-controls-service: 7007
REM   - compliance-agent-service: 7008
REM   - ai-analysis-service: 7009
REM   - mcp-boto3-server: 7010
REM   - api-gateway: 8000
REM =====================================================

setlocal enabledelayedexpansion

REM Calculate the ROOT directory (go up 2 levels from batch file location: scripts\batch -> root)
pushd "%~dp0..\.."
set "ROOT=%cd%"
popd

REM Check if virtual environments exist
echo Checking if virtual environments are set up...
if not exist "%ROOT%\gateway\.venv" (
    echo ERROR: Virtual environments not found. Please run install_venvs.bat first.
    pause
    exit /b 1
)

REM Check if Windows Terminal is available
where wt >nul 2>&1
if errorlevel 1 (
    echo.
    echo Windows Terminal not found. Opening services in separate CMD windows...
    echo.
    start "authentication-service (7001)" cmd /k "cd /d "%ROOT%\services\authentication-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7001 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "profile-service (7002)" cmd /k "cd /d "%ROOT%\services\profile-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7002 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "dashboard-service (7003)" cmd /k "cd /d "%ROOT%\services\dashboard-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7003 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "framework-category-service (7004)" cmd /k "cd /d "%ROOT%\services\framework-category-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7004 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "framework-service (7005)" cmd /k "cd /d "%ROOT%\services\framework-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7005 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "deployment-framework-service (7006)" cmd /k "cd /d "%ROOT%\services\deployment-framework-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7006 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "extract-controls-service (7007)" cmd /k "cd /d "%ROOT%\services\extract-controls-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7007 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "compliance-agent-service (7008)" cmd /k "cd /d "%ROOT%\services\compliance-agent-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7008 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "ai-analysis-service (7009)" cmd /k "cd /d "%ROOT%\services\ai-analysis-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7009 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "mcp-boto3-server (7010)" cmd /k "cd /d "%ROOT%\services\mcp-boto3-server" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7010 --reload --reload-dir . --reload-dir ..\..\shared"
    timeout /t 1 /nobreak
    start "api-gateway (8000)" cmd /k "cd /d "%ROOT%\gateway" && .venv\Scripts\activate.bat && python -m uvicorn main:app --host localhost --port 8000 --reload"
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
    new-tab --title "authentication-service (7001)" -d "%ROOT%\services\authentication-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7001 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "profile-service (7002)" -d "%ROOT%\services\profile-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7002 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "dashboard-service (7003)" -d "%ROOT%\services\dashboard-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7003 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "framework-category-service (7004)" -d "%ROOT%\services\framework-category-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7004 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "framework-service (7005)" -d "%ROOT%\services\framework-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7005 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "deployment-framework-service (7006)" -d "%ROOT%\services\deployment-framework-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7006 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "extract-controls-service (7007)" -d "%ROOT%\services\extract-controls-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7007 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "compliance-agent-service (7008)" -d "%ROOT%\services\compliance-agent-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7008 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "ai-analysis-service (7009)" -d "%ROOT%\services\ai-analysis-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7009 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "mcp-boto3-server (7010)" -d "%ROOT%\services\mcp-boto3-server" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7010 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "api-gateway (8000)" -d "%ROOT%\gateway" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn main:app --host localhost --port 8000 --reload" ^
    ; new-tab --title "frontend (Vite)" -d "%ROOT%\..\frontend" cmd /k "pnpm dev"

echo.
echo Windows Terminal opened with all services running in tabs.
