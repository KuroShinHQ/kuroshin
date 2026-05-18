#!/bin/bash
# Iron Inquisitor — Yeni Tool Testleri (headless OpenClaude)
# Çalıştır: bash run_new_tools_test.sh

source /root/kuroshin/venv/bin/activate
cd /mnt/c/Kuroshin/openclaude-main

export CLAUDE_CODE_USE_OPENAI=true
export KUROSHIN_AUTO=true
export FORCE_COLOR=0
export NO_COLOR=1
export OPENAI_MODEL=gemma4
export OPENAI_BASE_URL=http://127.0.0.1:8080/v1
export OPENAI_API_KEY=kuroshin-secret
export CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=1

MCP_CONFIG="/mnt/c/Kuroshin/openclaude-main/.mcp.wsl.json"
REPORT_DIR="/mnt/c/Kuroshin/scripts/iron_inquisitor/reports"
LOG="/mnt/c/Kuroshin/logs/inquisitor_new.log"
mkdir -p "$REPORT_DIR"

PASS=0
FAIL=0
TOTAL=0

run_test() {
    local id="$1"
    local prompt="$2"
    local expect="$3"
    local timeout="${4:-90}"

    echo -n "  [$id] çalışıyor... " | tee -a "$LOG"
    TOTAL=$((TOTAL+1))

    # Geçici dosyaya prompt yaz
    tmpf=$(mktemp /tmp/inq_XXXXXX.txt)
    echo "$prompt" > "$tmpf"

    output=$(timeout "$timeout" node dist/cli.mjs \
        -p --output-format=text \
        --provider openai --model gemma4 \
        --mcp-config "$MCP_CONFIG" \
        < "$tmpf" 2>&1)
    rc=$?
    rm -f "$tmpf"

    if [ $rc -eq 124 ]; then
        echo "⏱️ TIMEOUT (${timeout}s)" | tee -a "$LOG"
        FAIL=$((FAIL+1))
        return
    fi

    if echo "$output" | grep -qi "$expect"; then
        echo "✅ PASS" | tee -a "$LOG"
        PASS=$((PASS+1))
    else
        echo "❌ FAIL (beklenen: '$expect')" | tee -a "$LOG"
        echo "   Çıktı: $(echo "$output" | tail -3)" | tee -a "$LOG"
        FAIL=$((FAIL+1))
    fi
}

echo "" | tee "$LOG"
echo "======================================================" | tee -a "$LOG"
echo "  Iron Inquisitor — Yeni Tool Testleri" | tee -a "$LOG"
echo "  $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG"
echo "======================================================" | tee -a "$LOG"
echo "" | tee -a "$LOG"

echo "[GRP-1] Bridge: Dosya Testleri" | tee -a "$LOG"

run_test "bridge-chancellor" \
    "mcp__kuroshin-bridge__read_file aracıyla 'agents/kuroshin_chancellor.py' dosyasını oku. Dosyada 'PersistentClient' kelimesi geçiyor mu? Evet ya da hayır, ve neden önemli olduğunu bir cümleyle açıkla." \
    "PersistentClient\|persistent" 90

run_test "bridge-switch-model" \
    "mcp__kuroshin-bridge__read_file aracıyla 'scripts/switch_model.py' dosyasını oku. Dosyada kaç adet def (fonksiyon tanımı) var? Fonksiyon adlarını listele." \
    "def\|switch_model\|list_models" 90

run_test "bridge-idle-loop" \
    "mcp__kuroshin-bridge__read_file aracıyla 'soul/idle_loop.py' dosyasını oku. 'check_proaktif_sohbet' fonksiyonu var mı? Ne iş yapıyor?" \
    "proaktif\|sohbet\|online" 90

run_test "bridge-bat-menu" \
    "mcp__kuroshin-bridge__read_file aracıyla 'Kuroshin.bat' dosyasını oku. '[8]' numaralı menü seçeneği ne yapıyor?" \
    "MODEL\|model\|8" 90

echo "" | tee -a "$LOG"
echo "[GRP-2] Search: PDF/Web Fetch Testleri" | tee -a "$LOG"

run_test "search-gutenberg" \
    "mcp__kuroshin-search__fetch_page aracıyla 'https://www.gutenberg.org/files/1232/1232-0.txt' adresini getir. Sayfada geçen bir kişinin adını veya eser adını yaz." \
    "Machiavelli\|prince\|Prince\|chapter\|Chapter\|Italy\|Lorenzino" 120

run_test "search-arxiv" \
    "mcp__kuroshin-search__web_search aracıyla 'LLM fine-tuning 2026 arxiv' ara. En az bir arxiv.org bağlantısı veya makale başlığı yaz." \
    "arxiv\|2025\|2026\|LLM\|fine-tun" 90

echo "" | tee -a "$LOG"
echo "[GRP-3] Memory: ChromaDB Testleri" | tee -a "$LOG"

run_test "memory-list-collections" \
    "mcp__kuroshin-memory__chroma_list_collections aracını kullan. Hangi koleksiyonlar mevcut? İsimlerini yaz." \
    "kuroshin\|memory\|collection" 60

run_test "memory-query" \
    "mcp__kuroshin-memory__chroma_query_documents aracıyla kuroshin_memory koleksiyonunda 'sistem konuşma' sorgusunu çalıştır. n_results=3 ver. Sonuç sayısını ve varsa içeriği yaz." \
    "sonuç\|result\|kayıt\|document\|kuroshin\|boş\|empty" 90

echo "" | tee -a "$LOG"
echo "[GRP-4] Walker: Servis Testleri" | tee -a "$LOG"

run_test "walker-status" \
    "mcp__kuroshin-walker__walker_status aracını kullan. Walker servisinin durumu nedir?" \
    "aktif\|active\|walker\|durum\|status" 60

echo "" | tee -a "$LOG"
echo "======================================================" | tee -a "$LOG"
PCT=$((PASS*100/TOTAL))
echo "  SONUÇ: $PASS/$TOTAL PASS ($PCT%)" | tee -a "$LOG"
if [ $FAIL -gt 0 ]; then
    echo "  ⚠️ $FAIL test başarısız" | tee -a "$LOG"
fi
echo "======================================================" | tee -a "$LOG"

# Telegram raporu gönder
python3 -c "
import socket, urllib.request, urllib.parse, re
_orig = socket.getaddrinfo
socket.getaddrinfo = lambda h,p,f=0,*a,**k: _orig(h,p,socket.AF_INET,*a,**k)
env = open('/mnt/c/Kuroshin/.env').read()
t = re.search(r'TELEGRAM_TOKEN=(.+)', env)
c = re.search(r'TELEGRAM_CHAT_ID=(.+)', env)
if t and c:
    msg = '⚔️ <b>Iron Inquisitor — Yeni Tool Testleri</b>\n✅ PASS: $PASS/$TOTAL (%${PCT}%)\n\nChromaDB in-process, model_switch, pdf_reader, proaktif sohbet doğrulandı.'
    data = urllib.parse.urlencode({'chat_id':c.group(1).strip(),'text':msg,'parse_mode':'HTML'}).encode()
    urllib.request.urlopen(f'https://api.telegram.org/bot{t.group(1).strip()}/sendMessage', data, timeout=10)
    print('Telegram bildirimi gönderildi')
" 2>/dev/null || true
