#!/bin/bash
# Kuroshin boot bildirimi - Telegram'a asama raporu gonderir
# Kullanim: boot_notify.sh <adim> <toplam> <mesaj> [etiket]

# .env dosyasindan okunur (export TELEGRAM_TOKEN=... / export TELEGRAM_CHAT_ID=...)
TOKEN="${TELEGRAM_TOKEN:?TELEGRAM_TOKEN .env'de tanimli degil — export TELEGRAM_TOKEN=...}"
CHAT_ID="${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID .env'de tanimli degil — export TELEGRAM_CHAT_ID=...}"
TELEGRAM_URL="https://api.telegram.org/bot${TOKEN}/sendMessage"
TIMEOUT=8

STEP=$1
TOTAL=$2
MSG=$3
TAG=${4:-"INFO"}

build_bar() {
    local step=$1
    local total=$2
    local filled=$(( step * 10 / total ))
    local empty=$(( 10 - filled ))
    local bar=""

    for ((i=0; i<filled; i++)); do bar+="#"; done
    for ((i=0; i<empty; i++)); do bar+="-"; done

    local pct=$(( step * 100 / total ))
    echo "[${bar}] %${pct}"
}

BAR=$(build_bar "$STEP" "$TOTAL")
TEXT="[${TAG}] Kuroshin Uyaniyor [${STEP}/${TOTAL}]
${BAR}
${MSG}"

curl -s -m "$TIMEOUT" -X POST "$TELEGRAM_URL" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${CHAT_ID}\",\"text\":$(echo "$TEXT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" \
    >/dev/null 2>&1 &
