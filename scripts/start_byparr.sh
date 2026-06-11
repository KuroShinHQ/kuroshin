#!/bin/bash
# Byparr — Cloudflare Turnstile + PerimeterX bypass servisi (11 Haz 2026)
# Port 8191 | FlareSolverr uyumlu API | Camoufox tabanlı
# Kullanım: bash start_byparr.sh
set -uo pipefail

BYPARR_DIR="/tmp/byparr"
LOG="/mnt/c/Kuroshin/logs/byparr.log"
PORT=8191

# Zaten çalışıyorsa çık
if curl -s --max-time 2 "http://127.0.0.1:${PORT}/health" | grep -q "ok\|healthy\|status" 2>/dev/null; then
    echo "[BYPARR] Zaten aktif (port ${PORT})"
    exit 0
fi

# Eski process temizle
fuser -k ${PORT}/tcp >/dev/null 2>&1 || true
sleep 1

# Repo yoksa klonla
if [ ! -d "$BYPARR_DIR" ]; then
    echo "[BYPARR] Repo klonlanıyor..."
    git clone --depth=1 https://github.com/ThePhaseless/Byparr "$BYPARR_DIR" >> "$LOG" 2>&1
fi

# uv kurulu değilse kur
if ! command -v uv >/dev/null 2>&1; then
    source /root/.local/bin/env 2>/dev/null || true
fi
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >> "$LOG" 2>&1
    source /root/.local/bin/env
fi

# Camoufox binary kontrol
cd "$BYPARR_DIR"
source /root/.local/bin/env 2>/dev/null || true
uv run python -m camoufox fetch >> "$LOG" 2>&1 || true

# Başlat
echo "[BYPARR] Başlatılıyor (port ${PORT})..." | tee -a "$LOG"
setsid uv run main.py </dev/null >>"$LOG" 2>&1 &
BYPID=$!
echo $BYPID > /tmp/kuroshin_byparr.pid

# Hazır mı bekle (max 20s)
for i in $(seq 1 10); do
    sleep 2
    if curl -s --max-time 2 "http://127.0.0.1:${PORT}/docs" >/dev/null 2>&1; then
        echo "[BYPARR] ✅ AKTİF (PID $BYPID, port ${PORT})"
        exit 0
    fi
done

echo "[BYPARR] ⚠️ ${PORT} açılmadı ama devam ediliyor (lazy start olabilir)"
exit 0
