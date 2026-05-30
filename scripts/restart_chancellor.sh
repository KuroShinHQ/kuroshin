#!/bin/bash
# Chancellor'ı yeniden başlat
kill -9 $(cat /tmp/kuroshin_chancellor.pid 2>/dev/null) 2>/dev/null

# Crawlee bridge port 3006 — çalışmıyorsa başlat
if ! curl -s --max-time 2 http://127.0.0.1:3006/health > /dev/null 2>&1; then
    pkill -f crawlee_bridge 2>/dev/null
    setsid node /mnt/c/Kuroshin/tools/crawlee_bridge.js \
        >> /mnt/c/Kuroshin/logs/crawlee_bridge.log \
        2>> /mnt/c/Kuroshin/logs/crawlee_bridge_err.log &
fi
sleep 1
rm -f /tmp/kuroshin_chancellor.lock /tmp/kuroshin_chancellor.pid
source /root/kuroshin/venv/bin/activate
nohup python3 /mnt/c/Kuroshin/agents/kuroshin_chancellor.py >> /mnt/c/Kuroshin/logs/chancellor.log 2>&1 &
sleep 3
PID=$(cat /tmp/kuroshin_chancellor.pid 2>/dev/null)
if [ -n "$PID" ]; then
    echo "✅ Chancellor başlatıldı (PID: $PID)"
else
    echo "⚠️ PID dosyası bulunamadı — log kontrol edin"
    tail -5 /mnt/c/Kuroshin/logs/chancellor.log
fi
