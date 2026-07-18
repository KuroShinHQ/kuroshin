# =====================================================================
# SADECE ÇEREZ TEMİZLİK BETİĞİ (GÜVENLİ - Şifreler Silinmez)
# Bu işlem tüm açık oturumları kapatacaktır, ancak şifreleriniz kalacaktır.
# =====================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 1. TARAYICILAR KAPATILIYOR..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Stop-Process -Name "chrome","msedge","brave","opera" -Force -ErrorAction SilentlyContinue

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 2. SADECE ÇEREZLER SİLINİYOR (Şifreler Korunuyor)..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

# Chrome
Write-Host "Chrome çerezleri temizleniyor..." -ForegroundColor Gray
Remove-Item "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Network\Cookies" -Force -ErrorAction SilentlyContinue

# Edge
Write-Host "Edge çerezleri temizleniyor..." -ForegroundColor Gray
Remove-Item "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Network\Cookies" -Force -ErrorAction SilentlyContinue

# Brave
Write-Host "Brave çerezleri temizleniyor..." -ForegroundColor Gray
Remove-Item "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\User Data\Default\Network\Cookies" -Force -ErrorAction SilentlyContinue

# Opera
Write-Host "Opera çerezleri temizleniyor..." -ForegroundColor Gray
Remove-Item "$env:APPDATA\Opera Software\Opera Stable\Network\Cookies" -Force -ErrorAction SilentlyContinue

Write-Host "========================================" -ForegroundColor Green
Write-Host "ÇEREZ TEMİZLİĞİ TAMAMLANDI! ŞİFRELERİNİZ GÜVENDE." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
