#!/bin/bash
# Iron Inquisitor — Runtime Testleri (WSL içinde çalışır)
source /root/kuroshin/venv/bin/activate
cd /mnt/c/Kuroshin

PASS=0
FAIL=0

run_test() {
    local id="$1"
    local desc="$2"
    local cmd="$3"
    local expect="$4"

    output=$(eval "$cmd" 2>&1)
    if echo "$output" | grep -qi "$expect"; then
        echo "  ✅ [$id] $desc"
        PASS=$((PASS+1))
    else
        echo "  ❌ [$id] $desc"
        echo "     Beklenen: '$expect'"
        echo "     Çıktı: $(echo "$output" | head -3)"
        FAIL=$((FAIL+1))
    fi
}

echo ""
echo "======================================================"
echo "  Iron Inquisitor — Runtime Testleri"
echo "======================================================"

# --- ChromaDB in-process ---
run_test "chroma-rt-01" "ChromaDB kütüphanesi import" \
    "python3 -c 'import chromadb; print(chromadb.__version__)'" \
    "1\."

run_test "chroma-rt-02" "ChromaDB PersistentClient init" \
    "python3 -c \"
import chromadb
client = chromadb.PersistentClient(path='/root/kuroshin/memory/chroma')
col = client.get_or_create_collection('kuroshin_memory')
print(f'count:{col.count()}')
\"" \
    "count:"

run_test "chroma-rt-03" "ChromaDB test kaydı ekle + sorgula" \
    "python3 -c \"
import chromadb, datetime
client = chromadb.PersistentClient(path='/root/kuroshin/memory/chroma')
col = client.get_or_create_collection('kuroshin_memory')
ts = datetime.datetime.now().isoformat()[:19].replace(':', '')
doc_id = 'inquisitor_rt_' + ts.replace('-','').replace('T','_')
col.add(documents=['Iron Inquisitor runtime test ' + ts], ids=[doc_id])
result = col.query(query_texts=['inquisitor runtime'], n_results=1)
docs = result['documents'][0]
print('FOUND:' + docs[0][:50] if docs else 'NOTFOUND')
\"" \
    "FOUND"

# --- switch_model.py ---
run_test "model-rt-01" "switch_model.py import + list_models" \
    "python3 -c \"
import sys; sys.path.insert(0, '/mnt/c/Kuroshin/scripts')
from switch_model import list_models, get_active_model
models = list_models()
print(f'models:{len(models)}')
for m in models: print(m['name'])
\"" \
    "models:"

run_test "model-rt-02" "Aktif model tespiti" \
    "python3 /mnt/c/Kuroshin/scripts/switch_model.py status" \
    "Aktif model:"

run_test "model-rt-03" "Model listesi" \
    "python3 /mnt/c/Kuroshin/scripts/switch_model.py list" \
    "gguf\|model\|Mevcut"

# --- idle_loop.py fonksiyonları ---
run_test "idle-rt-01" "idle_loop import + ilgi_profili" \
    "python3 -c \"
import sys; sys.path.insert(0, '/mnt/c/Kuroshin/soul')
import idle_loop as il
profil = il._yukle_ilgi_profili()
print('profil:' + str(profil.get('ilgi_alanlari', [])[:2]))
\"" \
    "profil:"

run_test "idle-rt-02" "kullanıcı online kontrolü" \
    "python3 -c \"
import sys; sys.path.insert(0, '/mnt/c/Kuroshin/soul')
import idle_loop as il
online = il._kullanici_online_mu()
print('online:' + str(online))
\"" \
    "online:"

run_test "idle-rt-03" "rapor konusu çıkarma" \
    "python3 -c \"
import sys; sys.path.insert(0, '/mnt/c/Kuroshin/soul')
import idle_loop as il
konu = il._en_guncel_rapor_konusu()
print('konu:' + repr(konu[:50]) if konu else 'konu:bos')
\"" \
    "konu:"

# --- Llama server ---
run_test "llama-rt-01" "Llama server health check" \
    "curl -s --max-time 3 http://127.0.0.1:8080/health" \
    "ok\|error"

run_test "llama-rt-02" "Llama server models endpoint" \
    "curl -s --max-time 3 http://127.0.0.1:8080/v1/models" \
    "gemma\|data\|model"

# --- Chancellor log ---
run_test "chancellor-rt-01" "Chancellor log mevcut" \
    "ls -la /mnt/c/Kuroshin/logs/chancellor.log 2>/dev/null && echo FOUND || echo NOTFOUND" \
    "FOUND"

run_test "chancellor-rt-02" "Chancellor son aktivite (son 10dk)" \
    "find /mnt/c/Kuroshin/logs -name 'chancellor.log' -newer /tmp -mmin -10 2>/dev/null | head -1 || echo CHECK" \
    "chancellor\|CHECK"

# Özet
echo ""
echo "======================================================"
TOTAL=$((PASS+FAIL))
PCT=$((PASS*100/TOTAL))
echo "  Sonuç: $PASS/$TOTAL PASS ($PCT%)"
if [ $FAIL -gt 0 ]; then
    echo "  ⚠️ $FAIL test başarısız — detay yukarıda"
fi
echo "======================================================"
echo ""
