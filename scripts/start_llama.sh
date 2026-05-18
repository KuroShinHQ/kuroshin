#!/bin/bash
# Llama-server başlatıcı
MODEL="/root/kuroshin/models/mlabonne_Qwen3-8B-abliterated-Q5_K_M.gguf"
BIN="/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
LOG="/mnt/c/Kuroshin/logs/llama-server.log"

pkill -9 -f llama-server 2>/dev/null
sleep 1

nohup "$BIN" -m "$MODEL" \
    --host 0.0.0.0 --port 8080 \
    -ngl 99 -c 40960 -fa on \
    -ctk q4_0 -ctv q4_0 \
    --embeddings --mlock --no-mmap \
    --spec-type ngram-cache --draft-max 16 --draft-min 2 --draft-p-min 0.7 \
    >> "$LOG" 2>&1 &

echo "llama-server PID $! baslatildi, 8080 portu bekleniyor..."

# Health check bekle (max 90s)
for i in $(seq 1 45); do
    sleep 2
    if curl -s --max-time 2 http://127.0.0.1:8080/health | grep -q ok; then
        echo "llama-server HAZIR ($((i*2))s)"
        exit 0
    fi
done
echo "UYARI: 90s icinde yanit yok"
exit 1
