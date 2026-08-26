@echo off
set /p PGPASSWORD="Enter PostgreSQL password: "

echo Exporting schema...
"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h localhost -p 5432 -U postgres -d vora --schema-only --no-owner --no-privileges -f schema.sql

if %ERRORLEVEL% NEQ 0 (
    echo Failed to export schema.
    pause
    exit /b %ERRORLEVEL%
)

echo Exporting sample data...
powershell -ExecutionPolicy Bypass -File .\export-sample-data.ps1

echo Done!
pause
