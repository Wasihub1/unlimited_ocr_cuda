@echo off
rem Setup validates every step before run.py may start the server.
setlocal
cd /d "%~dp0"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set HF_HUB_DISABLE_TELEMETRY=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
if errorlevel 1 (
    echo [ERROR] Setup failed. See the step and reason above or logs\setup.log.
    pause
    exit /b 1
)
"%~dp0env\Scripts\python.exe" "%~dp0run.py" --skip-install %*
if errorlevel 1 (
    echo [ERROR] Server failed. See logs\setup.log.
    pause
    exit /b 1
)
exit /b 0
