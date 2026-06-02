#!/bin/bash
# Kuroshin SYSTEM_PAUSED.flag check — Lord direktifi 2 Haz 2026
# Kullanim: start scripts'lerin basina ekle:
#   source /mnt/c/Kuroshin/scripts/_check_system_paused.sh
# Eger memory/SYSTEM_PAUSED.flag varsa script exit 0 ile cikar (sessiz)
FLAG_FILE="/mnt/c/Kuroshin/memory/SYSTEM_PAUSED.flag"
if [ -f "$FLAG_FILE" ]; then
    echo "[SYSTEM_PAUSED] $0 atlandi — Lord menu 5 ile sistemi durdurdu (flag: $FLAG_FILE)"
    # Eger Telegram bildirim istersek ileride buraya eklenebilir
    exit 0
fi
