#!/bin/bash
# SYSTEM_PAUSED.flag check (Lord direktifi 2 Haz 2026)
source /mnt/c/Kuroshin/scripts/_check_system_paused.sh
source /root/kuroshin/venv/bin/activate
cd /mnt/c/Kuroshin/agents
export PYTHONUNBUFFERED=1
LOG=/root/kuroshin/logs/walker.log
# Stdout ve stderr'i log dosyasına yönlendir (shell seviyesinde)
exec 1>>"$LOG" 2>&1
exec python3 -u -m uvicorn kuroshin_walker_service:app \
    --host 127.0.0.1 \
    --port 9002 \
    --loop asyncio \
    --log-level warning
