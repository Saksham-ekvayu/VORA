@echo off
setlocal enabledelayedexpansion

REM Calculate the ROOT directory (go up 2 levels from batch file location: scripts\batch -> root)
pushd "%~dp0..\.."
set "ROOT=%cd%"
popd

REM Check if Windows Terminal is available
where wt >nul 2>&1
if errorlevel 1 (
    echo Windows Terminal not found. Opening services in separate CMD windows...
    start "authentication-service" cmd /k "cd /d "%ROOT%\services\authentication-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7001 --reload --reload-dir . --reload-dir ..\..\shared"
    start "profile-service" cmd /k "cd /d "%ROOT%\services\profile-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7002 --reload --reload-dir . --reload-dir ..\..\shared"
    start "dashboard-service" cmd /k "cd /d "%ROOT%\services\dashboard-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7003 --reload --reload-dir . --reload-dir ..\..\shared"
    start "framework-category-service" cmd /k "cd /d "%ROOT%\services\framework-category-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7004 --reload --reload-dir . --reload-dir ..\..\shared"
    start "framework-service" cmd /k "cd /d "%ROOT%\services\framework-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7005 --reload --reload-dir . --reload-dir ..\..\shared"
    start "deployment-framework-service" cmd /k "cd /d "%ROOT%\services\deployment-framework-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7006 --reload --reload-dir . --reload-dir ..\..\shared"
    start "comparison-service" cmd /k "cd /d "%ROOT%\services\comparison-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7008 --reload --reload-dir . --reload-dir ..\..\shared"
    start "compliance-agent-service" cmd /k "cd /d "%ROOT%\services\compliance-agent-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7009 --reload --reload-dir . --reload-dir ..\..\shared"
    start "deployment-gap-service" cmd /k "cd /d "%ROOT%\services\deployment-gap-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7010 --reload --reload-dir . --reload-dir ..\..\shared"
    start "extract-controls-service" cmd /k "cd /d "%ROOT%\services\extract-controls-service" && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7011 --reload --reload-dir . --reload-dir ..\..\shared"
    start "api-gateway" cmd /k "cd /d "%ROOT%\gateway" && .venv\Scripts\activate.bat && python -m uvicorn main:app --host localhost --port 8000 --reload"
    pause
    exit /b
)

REM Open Windows Terminal with tabs for each service
wt -w new new-tab --title "authentication-service" -d "%ROOT%\services\authentication-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7001 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "profile-service" -d "%ROOT%\services\profile-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7002 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "dashboard-service" -d "%ROOT%\services\dashboard-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7003 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "framework-category-service" -d "%ROOT%\services\framework-category-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7004 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "framework-service" -d "%ROOT%\services\framework-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7005 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "deployment-framework-service" -d "%ROOT%\services\deployment-framework-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7006 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "comparison-service" -d "%ROOT%\services\comparison-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7008 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "compliance-agent-service" -d "%ROOT%\services\compliance-agent-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7009 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "deployment-gap-service" -d "%ROOT%\services\deployment-gap-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7010 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "extract-controls-service" -d "%ROOT%\services\extract-controls-service" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --host localhost --port 7011 --reload --reload-dir . --reload-dir ..\..\shared" ^
    ; new-tab --title "api-gateway" -d "%ROOT%\gateway" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn main:app --host localhost --port 8000 --reload"
