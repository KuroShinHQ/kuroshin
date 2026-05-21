#!/bin/bash
# Llama-server başlatıcı — active_model.json'dan dinamik model okur
STATE_FILE="/mnt/c/Kuroshin/memory/active_model.json"
BIN="/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
LOG="/mnt/c/Kuroshin/logs/llama-server.log"
FALLBACK_MODEL="/root/kuroshin/models/mlabonne_Qwen3-8B-abliterated-Q5_K_M.gguf"
FALLBACK_CTX=32768

# active_model.json'dan model yolu ve context oku
if [ -f "$STATE_FILE" ]; then
    MODEL=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('path',''))" 2>/dev/null)
    CTX=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('context_size','') or '')" 2>/dev/null)
fi

# Fallback
[ -z "$MODEL" ] || [ ! -f "$MODEL" ] && MODEL="$FALLBACK_MODEL"
[ -z "$CTX" ] && CTX=$FALLBACK_CTX

MODEL_NAME=$(basename "$MODEL")
echo "Model: $MODEL_NAME (ctx=$CTX)"

# MoE tespiti: isimde a3b, moe, -ax varsa MoE
is_moe=0
echo "$MODEL_NAME" | grep -qiE '(a3b|moe|-ax)' && is_moe=1

if [ $is_moe -eq 1 ]; then
    EXTRA_PARAMS='-ot "exps=CPU"'
    echo "MoE modu: expert'ler CPU'ya alınıyor"
else
    EXTRA_PARAMS="--spec-type ngram-cache --draft-max 16 --draft-min 2 --draft-p-min 0.7"
    echo "Dense modu: speculative decoding aktif"
fi

pkill -9 -f llama-server 2>/dev/null
sleep 1

eval nohup "$BIN" -m "$MODEL" \
    --host 0.0.0.0 --port 8080 \
    -ngl 99 -c "$CTX" -fa on \
    -ctk q4_0 -ctv q4_0 \
    --embeddings --mlock --no-mmap \
    $EXTRA_PARAMS \
    >> "$LOG" 2>&1 &

echo "llama-server PID $! baslatildi, 8080 portu bekleniyor..."

for i in $(seq 1 45); do
    sleep 2
    if curl -s --max-time 2 http://127.0.0.1:8080/health | grep -q ok; then
        echo "llama-server HAZIR ($((i*2))s)"
        exit 0
    fi
done
echo "UYARI: 90s icinde yanit yok"
exit 1
