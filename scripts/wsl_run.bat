@echo off
:: WSL komut çalıştırıcı — PowerShell PTY sorunu bypass
:: Kullanım: wsl_run.bat "komut"
wsl -d Ubuntu-22.04 --exec /bin/bash -c "%~1"
