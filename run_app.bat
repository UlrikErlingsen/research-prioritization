@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo Learn Signal needs Python 3.10 or newer.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating Learn Signal's private Python environment...
  py -m venv .venv
)
".venv\Scripts\python.exe" -c "import streamlit, plotly, openpyxl, jsonschema" >nul 2>&1
if errorlevel 1 (
  echo Installing Learn Signal's open-source packages...
  ".venv\Scripts\python.exe" -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
if not defined ARROW_DEFAULT_MEMORY_POOL set ARROW_DEFAULT_MEMORY_POOL=system
if "%LEARNSIGNAL_PORT%"=="" set LEARNSIGNAL_PORT=8601
if "%LEARNSIGNAL_MAX_UPLOAD_MB%"=="" set LEARNSIGNAL_MAX_UPLOAD_MB=10000
echo Starting Learn Signal at http://127.0.0.1:%LEARNSIGNAL_PORT% ...
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=%LEARNSIGNAL_PORT% --server.maxUploadSize=%LEARNSIGNAL_MAX_UPLOAD_MB% --server.fileWatcherType=none --browser.gatherUsageStats=false
if errorlevel 1 pause
