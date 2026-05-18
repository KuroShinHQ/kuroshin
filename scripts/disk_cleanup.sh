#!/usr/bin/env bash
# disk_cleanup.sh — Günlük otomatik disk temizliği
# Crontab: 0 3 * * * bash /mnt/c/Kuroshin/scripts/disk_cleanup.sh >> /mnt/c/Kuroshin/logs/disk_cleanup.log 2>&1

set -euo pipefail
LOG="/mnt/c/Kuroshin/logs/disk_cleanup.log"
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"
TELEGRAM_CHAT="${TELEGRAM_CHAT_ID:-}"

_log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

_telegram() {
    [[ -z "$TELEGRAM_TOKEN" || -z "$TELEGRAM_CHAT" ]] && return 0
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT" -d text="$1" -d parse_mode="HTML" >/dev/null 2>&1 || true
}

_log "=== Disk temizliği başlıyor ==="
DISK_BEFORE=$(df -h /mnt/c 2>/dev/null | tail -1 | awk '{print $5}' || echo "?")

# pip cache temizliği
if command -v pip3 &>/dev/null; then
    pip3 cache purge --quiet 2>/dev/null && _log "pip cache temizlendi" || _log "pip cache: hata (devam)"
fi

# journalctl vacuum (WSL'de genelde yok ama güvenli)
if command -v journalctl &>/dev/null; then
    journalctl --vacuum-time=7d --quiet 2>/dev/null && _log "journalctl vacuum: 7 günden eski loglar silindi" || true
fi

# Kuroshin loglarını 10MB'yi aşanları sıfırla (RotatingFileHandler zaten 5MB kesiyor ama eski birikmişleri temizle)
for f in /mnt/c/Kuroshin/logs/*.log; do
    [[ -f "$f" ]] || continue
    SIZE=$(stat -c%s "$f" 2>/dev/null || echo 0)
    if [[ "$SIZE" -gt $((10 * 1024 * 1024)) ]]; then
        _log "Büyük log silindi: $(basename $f) ($(( SIZE / 1024 / 1024 ))MB)"
        > "$f"
    fi
done

# WSL geçici dosyaları
find /tmp -maxdepth 1 -name "kuroshin_*" -mtime +1 -delete 2>/dev/null && _log "/tmp kuroshin_* dosyaları temizlendi" || true

# HF cache — 14 günden eski snapshot'ları sil
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}/hub"
if [[ -d "$HF_CACHE" ]]; then
    OLD_SIZE=$(du -sh "$HF_CACHE" 2>/dev/null | cut -f1 || echo "?")
    find "$HF_CACHE" -name "*.incomplete" -mtime +1 -delete 2>/dev/null || true
    find "$HF_CACHE" -name "tmp*" -mtime +1 -delete 2>/dev/null || true
    _log "HF cache temizlendi (önceki boyut: $OLD_SIZE)"
fi

DISK_AFTER=$(df -h /mnt/c 2>/dev/null | tail -1 | awk '{print $5}' || echo "?")
MSG="🧹 Kuroshin disk temizliği tamamlandı
Önce: $DISK_BEFORE | Sonra: $DISK_AFTER"
_log "$MSG"
_telegram "$MSG"
