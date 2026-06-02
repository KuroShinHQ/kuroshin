#!/bin/bash
# SYSTEM_PAUSED.flag check (Lord direktifi 2 Haz 2026)
source /mnt/c/Kuroshin/scripts/_check_system_paused.sh
source /root/kuroshin/venv/bin/activate
cd /mnt/c/Kuroshin/agents
export PYTHONUNBUFFERED=1
python3 kuroshin_council_service.py >> /root/kuroshin/logs/council.log 2>&1
