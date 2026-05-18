@echo off
:: WSL Guardian — WSL bozuk state'te ise shutdown + restart yapar
:: Kuroshin.bat'tan veya Görev Zamanlayıcı'dan çalıştırılabilir

echo [WSL Guardian] WSL durumu kontrol ediliyor...

:: Basit test komutu dene
wsl -d Ubuntu-22.04 --exec /bin/bash -c "echo WSL_OK" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [WSL Guardian] WSL bozuk state tespit edildi. Yeniden baslatiliyor...
    wsl --shutdown
    timeout /t 3 /nobreak >nul
    echo [WSL Guardian] WSL yeniden baslatildi.
) else (
    echo [WSL Guardian] WSL saglıklı.
)
