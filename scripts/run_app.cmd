@echo off
cd /d "%~dp0\.."
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_app.ps1"
