#!/bin/bash
# DALGA 5.x Live Test — Inject + monitor sistem
set -e

INJECT_FILE="/tmp/kuroshin_test_inject.json"
LOG_FILE="/mnt/c/Kuroshin/logs/chancellor.log"

CHAT_ID="YOUR_TELEGRAM_CHAT_ID_HERE"
TEXT="${1:-Merhaba}"
TIMEOUT="${2:-90}"

# Log offset baslangic
START_LINES=$(wc -l < "$LOG_FILE")

# Inject
cat > "$INJECT_FILE" <<EOF
{"chat_id": $CHAT_ID, "text": "$TEXT", "test_mode": true}
EOF
echo "[INJECT] $(date +%T) chat_id=$CHAT_ID text='$TEXT' (test_mode=true)"

# Bekle ve log izle
deadline=$(($(date +%s) + TIMEOUT))
inject_seen=0
out_line=""
while [ "$(date +%s)" -lt "$deadline" ]; do
    sleep 2
    # yeni log satirlari
    cur_lines=$(wc -l < "$LOG_FILE")
    if [ "$cur_lines" -gt "$START_LINES" ]; then
        new=$(tail -n +$((START_LINES+1)) "$LOG_FILE")
        if echo "$new" | grep -q '\[INJECT\]'; then
            inject_seen=1
        fi
        if [ $inject_seen -eq 1 ]; then
            out=$(echo "$new" | grep '\[TELEGRAM_OUT\]' | tail -1)
            if [ -n "$out" ]; then
                out_line="$out"
                break
            fi
        fi
    fi
done

if [ -n "$out_line" ]; then
    elapsed=$(( $(date +%s) - (deadline - TIMEOUT) ))
    echo "[OK] (${elapsed}s) $out_line"
    exit 0
else
    echo "[TIMEOUT] ${TIMEOUT}s icinde TELEGRAM_OUT gorulmedi"
    echo "--- son 20 log satiri ---"
    tail -20 "$LOG_FILE"
    exit 1
fi
