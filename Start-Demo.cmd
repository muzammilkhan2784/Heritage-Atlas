@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" scripts\bootstrap.py
if errorlevel 1 goto fail
".venv\Scripts\python.exe" scripts\install_mongodb.py
if errorlevel 1 goto fail
".venv\Scripts\python.exe" scripts\run_local.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup stopped. Please read the error above.
pause
exit /b 1
