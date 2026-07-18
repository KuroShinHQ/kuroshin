#!/bin/bash
BIN="/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
MODEL="/mnt/c/Kuroshin/models/DeepSeek-R1-Distill-Qwen-32B-abliterated-Q4_K_M.gguf"
LOG="/mnt/c/Kuroshin/logs/llama-server.log"
pkill -9 -f llama-server 2>/dev/null
sleep 2
nohup $BIN -m $MODEL --host 0.0.0.0 --port 8080 -ngl 28 -c 16384 -fa on -ctk q4_0 -ctv q4_0 --embeddings --mlock --no-mmap --metrics --reasoning-budget 2048 --spec-type ngram-cache --draft-max 16 --draft-min 2 --draft-p-min 0.7 >> $LOG 2>&1 &
echo "DeepSeek PID $! baslatildi"
# Health check bekle
for i in $(seq 1 120); do
    sleep 2
    if curl -s --max-time 2 http://127.0.0.1:8080/health | grep -q ok; then
        echo "HAZIR ($((i*2))s)"
        exit 0
    fi
    if [ $((i % 10)) -eq 0 ]; then
        echo "yukleniyor... ($((i*2))s)"
    fi
done
echo "TIMEOUT"
exit 1
