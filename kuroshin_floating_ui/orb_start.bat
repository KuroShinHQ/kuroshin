@echo off
taskkill /F /IM Kuroshin.exe >nul 2>nul
taskkill /F /IM pythonw.exe >nul 2>nul
timeout /t 1 /nobreak >nul
if /i "%1"=="stop" exit /b 0
start "" /B "C:\Kuroshin\dist\Kuroshin\Kuroshin.exe" --mode lite
echo [ORB] Baslatildi.
