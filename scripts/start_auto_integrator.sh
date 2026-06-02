#!/bin/bash
# SYSTEM_PAUSED.flag check (Lord direktifi 2 Haz 2026)
source /mnt/c/Kuroshin/scripts/_check_system_paused.sh
source /root/kuroshin/venv/bin/activate
export PYTHONUNBUFFERED=1
exec python3 -u /mnt/c/Kuroshin/scripts/auto_integrator.py >> /root/kuroshin/logs/auto_integrator.log 2>&1
