#!/bin/bash
BIN="/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
MODEL="/mnt/c/Kuroshin/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
LOG="/mnt/c/Kuroshin/logs/llama-server.log"
pkill -9 -f llama-server 2>/dev/null
sleep 2
nohup $BIN -m $MODEL --host 0.0.0.0 --port 8080 -ngl 99 -c 16384 -fa on -ctk q4_0 -ctv q4_0 --embeddings --mlock --no-mmap --metrics >> $LOG 2>&1 &
echo "Qwen3-Coder baslatiliyor..."
for i in $(seq 1 90); do
    sleep 2
    if curl -s --max-time 2 http://127.0.0.1:8080/health | grep -q ok; then
        echo "HAZIR ($((i*2))s)"
        exit 0
    fi
done
echo "TIMEOUT"
exit 1
