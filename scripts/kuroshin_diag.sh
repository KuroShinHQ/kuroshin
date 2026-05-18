#!/bin/bash
# ============================================================
# KUROSHIN KARARGAH — TAM TANI SİSTEMİ v1.0
# ============================================================
# Kullanım: wsl -d Ubuntu-22.04 -- bash /mnt/c/Kuroshin/scripts/kuroshin_diag.sh
# Tüm servisleri, portları, logları ve hata kök nedenlerini raporlar.

VENV="/root/kuroshin/venv"
LOG_DIR="/root/kuroshin/logs"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[✅ OK ]${NC} $1"; }
fail() { echo -e "  ${RED}[❌ FAIL]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[⚠️  WARN]${NC} $1"; }
info() { echo -e "  ${CYAN}[ℹ️  INFO]${NC} $1"; }

check_port() {
    local name="$1" port="$2"
    local pid_info
    pid_info=$(ss -tlnp 2>/dev/null | grep ":${port} " | awk '{print $NF}')
    if [ -n "$pid_info" ]; then
        ok "${name} — port ${port} AKTİF ($pid_info)"
        return 0
    else
        fail "${name} — port ${port} KAPALI"
        return 1
    fi
}

check_http() {
    local name="$1" url="$2" expect="$3"
    local resp
    resp=$(curl -s --max-time 4 "$url" 2>/dev/null)
    if echo "$resp" | grep -q "${expect}"; then
        ok "${name} HTTP OK — $(echo "$resp" | head -c 80)"
    else
        fail "${name} HTTP FAIL — url: ${url} | yanıt: $(echo "$resp" | head -c 80)"
    fi
}

show_log_tail() {
    local name="$1" file="$2"
    if [ -f "$file" ]; then
        local lines
        lines=$(tail -5 "$file" 2>/dev/null)
        if echo "$lines" | grep -qiE "error|traceback|exception|failed|errno"; then
            warn "${name} logunda HATA var:"
            tail -8 "$file" | sed 's/^/    /'
        else
            info "${name} log temiz (son satır: $(tail -1 "$file" | cut -c1-80))"
        fi
    else
        warn "${name} log dosyası yok: $file"
    fi
}

echo ""
echo "================================================================"
echo "   🔱 KUROSHIN KARARGAH TAM TANI SİSTEMİ v1.0"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"

# ── BÖLÜM 1: VENV ────────────────────────────────────────────
echo ""
echo "${CYAN}── [1] PYTHON VENV ──────────────────────────────────────${NC}"
if [ -d "$VENV" ]; then
    ok "Venv mevcut: $VENV"
    PY_VER=$("$VENV/bin/python3" --version 2>&1)
    ok "Python: $PY_VER"
else
    fail "Venv yok: $VENV"
fi

# ── BÖLÜM 2: KRİTİK PAKETLER ────────────────────────────────
echo ""
echo "${CYAN}── [2] KRİTİK PAKETLER ─────────────────────────────────${NC}"
for pkg in mcp chromadb crawl4ai agno fastapi uvicorn ddgs httpx; do
    if "$VENV/bin/python3" -c "import $pkg" 2>/dev/null; then
        VER=$("$VENV/bin/python3" -c "import $pkg; print(getattr($pkg,'__version__','?'))" 2>/dev/null)
        ok "$pkg — v$VER"
    else
        fail "$pkg — KURULU DEĞİL (pip install $pkg)"
    fi
done

# ── BÖLÜM 3: SERVİS PORTLARİ ────────────────────────────────
echo ""
echo "${CYAN}── [3] SERVİS PORTLARI ─────────────────────────────────${NC}"
check_port "llama-server (Gemma4)"  8080
check_port "LiteLLM Proxy"          6000
check_port "ChromaDB HTTP"          8100
check_port "Walker Agent"           9002
check_port "Agent Bridge"           3005
check_port "Nuclear Search"         8091
check_port "OpenClaw (WhatsApp)"    18789

# ── BÖLÜM 4: HTTP SAĞLIK KONTROLLERİ ───────────────────────
echo ""
echo "${CYAN}── [4] HTTP SAĞLIK KONTROLLERİ ─────────────────────────${NC}"
check_http "llama-server"  "http://127.0.0.1:8080/health"           "ok"
check_http "ChromaDB"      "http://127.0.0.1:8100/api/v2/heartbeat" "heartbeat"
check_http "Walker"        "http://127.0.0.1:9002/status"           "ready"
check_http "Agent Bridge"  "http://127.0.0.1:3005/health"           "ok"

# LiteLLM — dinamik port sorunu var mı?
LITELLM_PORT=$(ss -tlnp 2>/dev/null | grep litellm | grep -oP ':\K[0-9]+' | head -1)
if [ -n "$LITELLM_PORT" ]; then
    if [ "$LITELLM_PORT" = "6000" ]; then
        ok "LiteLLM port doğru: 6000"
    else
        warn "LiteLLM YANLIŞ PORTTA: $LITELLM_PORT (beklenen 6000)"
        warn "Çözüm: Kuroshin.bat'taki LiteLLM komutunu kontrol et"
    fi
    check_http "LiteLLM" "http://127.0.0.1:${LITELLM_PORT}/v1/models" "data"
else
    fail "LiteLLM hiç çalışmıyor"
fi

# ── BÖLÜM 5: LOG HATA TARAMASI ──────────────────────────────
echo ""
echo "${CYAN}── [5] LOG HATA TARAMASI ────────────────────────────────${NC}"
show_log_tail "llama-server"   "$LOG_DIR/llama-server.log"
show_log_tail "LiteLLM"        "$LOG_DIR/litellm.log"
show_log_tail "ChromaDB"       "$LOG_DIR/chromadb.log"
show_log_tail "Walker"         "$LOG_DIR/walker.log"
show_log_tail "Agent Bridge"   "$LOG_DIR/agent_bridge.log"
show_log_tail "OpenClaw"       "$LOG_DIR/openclaw.log"
show_log_tail "Nuclear Search" "$LOG_DIR/search_engine.log"

# ── BÖLÜM 6: WSL2 REZERVE PORT TARAMASI ─────────────────────
echo ""
echo "${CYAN}── [6] WSL2 REZERVE PORT TARAMASI ──────────────────────${NC}"
RESERVED=$(powershell.exe -Command "netsh interface ipv4 show excludedportrange protocol=tcp 2>nul" 2>/dev/null | grep -oP '\d{4,5}' | sort -n)
for p in 9001 9002 9003 6000 3005 8100; do
    if echo "$RESERVED" | grep -q "^${p}$"; then
        warn "Port $p Windows tarafından REZERVE (değiştir)"
    fi
done
info "Windows rezerve port taraması tamamlandı"

# ── BÖLÜM 7: MCP SUNUCU KONFIGÜRASYONU ──────────────────────
echo ""
echo "${CYAN}── [7] MCP KONFIGÜRASYONU ───────────────────────────────${NC}"
MCP_FILE="/mnt/c/Kuroshin/openclaude-main/.mcp.json"
if [ -f "$MCP_FILE" ]; then
    ok ".mcp.json mevcut"
    SERVERS=$(python3 -c "import json; d=json.load(open('$MCP_FILE')); [print('    →',k) for k in d.get('mcpServers',{})]" 2>/dev/null)
    echo "$SERVERS"
else
    fail ".mcp.json bulunamadı: $MCP_FILE"
fi

# ── BÖLÜM 8: ÖZET ───────────────────────────────────────────
echo ""
echo "================================================================"
echo "   TANI TAMAMLANDI — Sorun varsa yukarıdaki [❌] satırlarına bak"
echo "================================================================"
echo ""
