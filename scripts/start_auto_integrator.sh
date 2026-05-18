#!/bin/bash
source /root/kuroshin/venv/bin/activate
export PYTHONUNBUFFERED=1
exec python3 -u /mnt/c/Kuroshin/scripts/auto_integrator.py >> /root/kuroshin/logs/auto_integrator.log 2>&1
