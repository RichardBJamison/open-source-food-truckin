@echo off
REM OSFT Windows installer / launcher
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found. Install Python 3.10+ from python.org and retry.
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating virtualenv...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
echo.
echo OSFT ready. Starting server on http://127.0.0.1:5053/
echo Press Ctrl+C to stop.
python server.py
pause
