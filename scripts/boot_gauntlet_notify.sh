#!/bin/bash
# Gauntlet sonucunu Telegram'a gönderir
TOKEN="YOUR_TELEGRAM_TOKEN_HERE"
CHAT_ID="YOUR_TELEGRAM_CHAT_ID_HERE"

TOTAL=7
LINES=""
PASS=0

ping_service() {
    local PORT="$1" ENDPOINT="$2"
    curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 5 "http://127.0.0.1:${PORT}${ENDPOINT}" 2>/dev/null
}

add_line() {
    local NAME="$1" PORT="$2" ENDPOINT="$3"
    local CODE
    CODE=$(ping_service "$PORT" "$ENDPOINT")
    if [[ "$CODE" =~ ^(200|201|204|401|405)$ ]]; then
        LINES+="✅ ${NAME}\n"
        PASS=$((PASS+1))
    else
        LINES+="❌ ${NAME} (${CODE:-TMT})\n"
    fi
}

add_line "llama-server"   8080 "/health"
add_line "ChromaDB"       8100 "/api/v2/heartbeat"
add_line "Walker"         9002 "/status"
add_line "Konsey"         9004 "/health"
add_line "Reranker"       9003 "/health"
add_line "Agent Bridge"   3005 "/health"
add_line "Nuclear Search" 8091 "/health"

if [ "$PASS" -ge 7 ]; then
    DURUM="🟢 SAĞLIKLI — İmparatorluk tam kapasite!"
elif [ "$PASS" -ge 5 ]; then
    DURUM="🟡 KISMİ — Bazı servisler eksik."
else
    DURUM="🔴 KRİTİK — Sistem sorunlu."
fi

MSG="🔱 <b>Kuroshin Boot Tamamlandı</b>
${PASS}/${TOTAL} servis aktif

$(echo -e "$LINES")

${DURUM}"

curl -s -m 10 -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${CHAT_ID}\",\"text\":$(echo "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'),\"parse_mode\":\"HTML\"}" \
    >/dev/null 2>&1
