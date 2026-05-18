#!/bin/bash
source /root/kuroshin/venv/bin/activate
export PYTHONUNBUFFERED=1
mkdir -p /root/kuroshin/memory/chroma
exec python3 -u -c "
import uvicorn, chromadb
from chromadb.config import Settings
from chromadb.server.fastapi import FastAPI
settings = Settings(
    is_persistent=True,
    persist_directory='/root/kuroshin/memory/chroma',
    anonymized_telemetry=False,
)
server = FastAPI(settings)
app = server.app()
uvicorn.run(app, host='0.0.0.0', port=8100, log_level='warning')
" >> /root/kuroshin/logs/chromadb.log 2>&1
