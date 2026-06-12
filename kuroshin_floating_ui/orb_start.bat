@echo off
taskkill /F /IM pythonw.exe >nul 2>nul
timeout /t 1 /nobreak >nul
if /i "%1"=="stop" exit /b 0
start "" /B pythonw "%~dp0main.py" --mode lite
echo [ORB] Baslatildi.
