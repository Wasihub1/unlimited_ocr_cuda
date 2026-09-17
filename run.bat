@echo off
cd /d "%~dp0"


if not exist "env\Scripts\python.exe" (
    echo [INFO] Environment not found. Creating virtual environment...
    python -m venv env
    if errorlevel 1 (
        echo [ERROR] Python is not installed or not added to PATH!
        pause
        exit /b 1
    )
    
    echo [INFO] Virtual environment created. Running setup.ps1...
    powershell -ExecutionPolicy Bypass -File setup.ps1
    
    if not exist "env\Scripts\python.exe" (
        echo [ERROR] Setup failed.
        pause
        exit /b 1
    )
)

"env\Scripts\python.exe" run.py --skip-install
pause