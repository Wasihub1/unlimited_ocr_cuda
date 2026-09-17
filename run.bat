@echo off
rem Setup caches weights separately; this launcher starts the existing environment.
cd /d "%~dp0"
if not exist "env\Scripts\python.exe" (
    echo Environment not found. Running setup.ps1 automatically...
    powershell -ExecutionPolicy Bypass -File setup.ps1
    if not exist "env\Scripts\python.exe" (
        echo Setup failed. Please check the messages above.
        pause
        exit /b 1
    )
)
"env\Scripts\python.exe" run.py --skip-install
pause