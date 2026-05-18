#!/bin/bash
source /root/kuroshin/venv/bin/activate
cd /mnt/c/Kuroshin/agents
export PYTHONUNBUFFERED=1
python3 kuroshin_council_service.py >> /root/kuroshin/logs/council.log 2>&1
