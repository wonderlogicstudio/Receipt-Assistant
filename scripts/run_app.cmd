@echo off
cd /d "%~dp0\.."
echo Starting Receipt Assistant Streamlit app with clean port restart...
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_app.ps1"
echo Streamlit stopped.
pause
