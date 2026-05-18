#!/bin/bash
# Chancellor'ı yeniden başlat
kill -9 $(cat /tmp/kuroshin_chancellor.pid 2>/dev/null) 2>/dev/null
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
