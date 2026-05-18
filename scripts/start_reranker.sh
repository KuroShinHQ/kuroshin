#!/bin/bash
source /root/kuroshin/venv/bin/activate
exec python3 /mnt/c/Kuroshin/scripts/kuroshin_reranker_service.py \
    >> /root/kuroshin/logs/reranker.log 2>&1
