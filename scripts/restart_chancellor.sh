#!/bin/bash
# Kuroshin Chancellor — SAĞLAM restart (31 May 2026)
# Dersler (bu turdan):
#   - nohup/& WSL'de SIGHUP ile ölür → setsid ŞART
#   - chancellor sessizce hang olabilir (startup yarım) → AKTİF + 8201 DOĞRULA, olmadıysa Telegram ALARM
#   - pkill -f crawlee_bridge KENDİ cmdline'ını öldürüyordu → fuser -k 3006/tcp
#   - SYSTEM_PROMPT değişince BLUE-NEURAL-01 PROMPT_TAMPERED verir → kasıtlıysa: restart_chancellor.sh --relock
set -uo pipefail
KURO=/mnt/c/Kuroshin
LOG=$KURO/logs/chancellor.log
VENV=/root/kuroshin/venv/bin/activate
RELOCK="${1:-}"

alert() {
    # .env'den Telegram token oku, alarm gönder (sessiz ölüm önleme)
    set +u
    [ -f "$KURO/.env" ] && . "$KURO/.env"
    if [ -n "${TELEGRAM_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -m 8 "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
            --data-urlencode "text=$1" >/dev/null 2>&1
    fi
    set -u
}

# Kasıtlı prompt değişikliğinde integrity re-lock (varsayılan: re-lock YOK — güvenlik kalsın)
if [ "$RELOCK" = "--relock" ]; then
    rm -f "$KURO/memory/prompt_integrity.json"
    echo "[restart] prompt_integrity.json silindi → bu başlangıçta yeni prompt'a re-lock olacak"
fi

# Crawlee bridge (port 3006) — çalışmıyorsa başlat (fuser ile, self-match yok)
if ! curl -s --max-time 2 http://127.0.0.1:3006/health >/dev/null 2>&1; then
    fuser -k 3006/tcp >/dev/null 2>&1
    sleep 1
    ( cd "$KURO/tools" && setsid node crawlee_bridge.js </dev/null \
        >>"$KURO/logs/crawlee_bridge.log" 2>>"$KURO/logs/crawlee_bridge_err.log" & )
fi

# Eski chancellor'ı öldür
OLD=$(cat /tmp/kuroshin_chancellor.pid 2>/dev/null || true)
[ -n "${OLD:-}" ] && kill -9 "$OLD" 2>/dev/null || true
sleep 2
rm -f /tmp/kuroshin_chancellor.lock /tmp/kuroshin_chancellor.pid

# Başlat — setsid ŞART (nohup/& SIGHUP ile ölür)
# shellcheck disable=SC1090
source "$VENV"
setsid python3 "$KURO/agents/kuroshin_chancellor.py" </dev/null >>"$LOG" 2>&1 &

# AKTİF + 8201 doğrula (max ~26s) — sessiz hang'i yakala
ok=0
for _ in $(seq 1 13); do
    sleep 2
    if curl -s -m 3 http://127.0.0.1:8201/health >/dev/null 2>&1 \
       && tail -n 50 "$LOG" | grep -q "Şansölye AKTİF"; then
        ok=1; break
    fi
done

PID=$(cat /tmp/kuroshin_chancellor.pid 2>/dev/null || true)
if [ "$ok" = "1" ] && [ -n "${PID:-}" ]; then
    echo "✅ Chancellor AKTİF (PID $PID)"
    if tail -n 50 "$LOG" | grep -q "PROMPT_TAMPERED"; then
        echo "⚠️ PROMPT_TAMPERED tespit edildi — SYSTEM_PROMPT değişmiş."
        echo "   Kasıtlıysa yeniden kilitle:  bash $KURO/scripts/restart_chancellor.sh --relock"
        alert "⚠️ Kuroshin: SYSTEM_PROMPT değişti (PROMPT_TAMPERED). Kasıtlıysa --relock ile yeniden kilitleyin."
    fi
    exit 0
else
    echo "❌ Chancellor AKTİF OLMADI (PID=${PID:-yok}) — startup hang/crash."
    echo "--- son log ---"
    tail -n 15 "$LOG"
    alert "🚨 Kuroshin: Chancellor restart BAŞARISIZ — AKTİF olmadı (hang/crash). Log kontrol edin."
    exit 1
fi
