#!/bin/bash
# KUROSHIN HEALTH CHECK v1.2 - FAZ 5 GAUNTLET

PASS=0
FAIL=0
TOTAL=0

check_port() {
    local NAME="$1"
    local PORT="$2"
    local ENDPOINT="$3"
    TOTAL=$((TOTAL + 1))

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 5 "http://127.0.0.1:${PORT}${ENDPOINT}" 2>/dev/null)

    if [[ "$HTTP_CODE" =~ ^(200|201|204|401|405)$ ]]; then
        echo "  PASS  ${NAME} (port ${PORT}) -> HTTP ${HTTP_CODE}"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  ${NAME} (port ${PORT}) -> HTTP ${HTTP_CODE:-TIMEOUT}"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "KUROSHIN HEALTH GAUNTLET v1.2 - $(date '+%d.%m.%Y %H:%M:%S')"
echo "======================================================="

check_port "llama-server (Qwen3)" 8080 "/health"
check_port "ChromaDB Memory"      8100 "/api/v2/heartbeat"
check_port "Walker Agent"         9002 "/status"
check_port "Ajan Konseyi"         9004 "/health"
check_port "BGE Reranker"         9003 "/health"
check_port "Agent Bridge"         3005 "/health"
check_port "Nuclear Search"       8091 "/health"

echo ""
echo "======================================================="
PCT=$(( PASS * 100 / TOTAL ))
echo "  SONUC: ${PASS}/${TOTAL} PASS (%${PCT})"

if [ "$PASS" -ge 7 ]; then
    echo "  SAGLIKLI - Imparatorluk tam kapasite."
elif [ "$PASS" -ge 5 ]; then
    echo "  KISMI - Bazi servisler eksik."
else
    echo "  KRITIK - Kuroshin.bat ile sistemi baslatin."
fi
echo ""
