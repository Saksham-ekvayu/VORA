@echo off
setlocal
set "ROOT=%~dp0..\.."
python "%ROOT%\scripts\create_venvs.py"
if errorlevel 1 (
    pause
    exit /b %errorlevel%
)
pause
