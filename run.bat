@echo off
rem Setup caches weights separately; this launcher starts the existing environment.
cd /d "%~dp0"
if not exist "env\Scripts\python.exe" (
    echo Run setup.ps1 first to prepare the environment and cache the model.
    pause
    exit /b 1
)
"env\Scripts\python.exe" run.py --skip-install
pause
