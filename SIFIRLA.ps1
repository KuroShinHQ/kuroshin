# =====================================================================
# SIFIR NOKTASI TEMİZLİK PROMTU - GÜVENLİ VERSİYON (Gemini CLI'yi öldürmez!)
# Yönetici olarak çalıştır!
# =====================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 1. ZARARLI NODE SÜREÇLERİ DURDURULUYOR (Gemini/Claude hariç)..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

Get-CimInstance Win32_Process -Filter "name = 'node.exe'" | ForEach-Object {
    $pid = $_.ProcessId
    $cmd = $_.CommandLine
    if ($cmd -match "gemini|claude|Gemini|Claude") {
        Write-Host "ATLANIYOR (Güvenli): PID $pid - Gemini/Claude CLI" -ForegroundColor Green
    } else {
        Write-Host "DURDURULUYOR (Şüpheli): PID $pid - $cmd" -ForegroundColor Red
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 2. WSL KAPATILIYOR..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
wsl --shutdown

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 3. BASLANGIC (STARTUP) KIRLI KAYITLAR TEMIZLENIYOR..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Kuroshin*" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Rave" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "ut" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Kuroshin*" -ErrorAction SilentlyContinue
Remove-Item -Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Kuroshin*.lnk" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Rave*.lnk" -Force -ErrorAction SilentlyContinue

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 4. DISCORD CASUS DOSYALARI TEMIZLENIYOR..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Remove-Item "$env:APPDATA\Discord" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Discord" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 5. GECICI DOSYALAR VE ONBELLEK TEMIZLENIYOR..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Windows\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\Kuroshin*" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 6. WINDOWS DEFENDER HIZLI TARAMA BASLATILIYOR..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Start-MpScan -ScanType QuickScan -ErrorAction SilentlyContinue

Write-Host "========================================" -ForegroundColor Green
Write-Host "TEMIZLIK TAMAMLANDI!" -ForegroundColor Green
Write-Host "NOT: Lutfen telefonundan tum sifrelerini degistir!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
