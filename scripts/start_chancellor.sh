#!/bin/bash
# Chancellor başlatıcı — WSL'den veya bat'tan çağrılır
LOG="/mnt/c/Kuroshin/logs/chancellor.log"

# Eski instance temizle
if [ -f /tmp/kuroshin_chancellor.pid ]; then
    OLD_PID=$(cat /tmp/kuroshin_chancellor.pid)
    kill -9 "$OLD_PID" 2>/dev/null
fi
rm -f /tmp/kuroshin_chancellor.lock /tmp/kuroshin_chancellor.pid

source /root/kuroshin/venv/bin/activate

# Yeni instance başlat (detached)
nohup python3 /mnt/c/Kuroshin/agents/kuroshin_chancellor.py \
    >> "$LOG" 2>&1 &

NEW_PID=$!
echo $NEW_PID > /tmp/kuroshin_chancellor.pid
echo "[start_chancellor] $(date '+%Y-%m-%d %H:%M:%S') PID $NEW_PID ile baslatildi" >> "$LOG"
echo "STARTED:$NEW_PID"
