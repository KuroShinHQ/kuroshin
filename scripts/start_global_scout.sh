#!/bin/bash
# --daemon: Kuroshin.bat'tan sürekli çalışır (while döngüsü)
# (argümansız): cron'dan tek seferlik çalışır
# SYSTEM_PAUSED.flag check (Lord direktifi 2 Haz 2026 — cron tetiklerinde de saygı)
source /mnt/c/Kuroshin/scripts/_check_system_paused.sh
source /root/kuroshin/venv/bin/activate
export PYTHONUNBUFFERED=1
mkdir -p /root/kuroshin/memory/scout_reports
exec python3 -u /mnt/c/Kuroshin/scripts/global_scout.py "$@" >> /root/kuroshin/logs/global_scout.log 2>&1
