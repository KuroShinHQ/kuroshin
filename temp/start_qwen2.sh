#!/bin/bash
BIN="/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
MODEL="/mnt/c/Kuroshin/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
LOG="/mnt/c/Kuroshin/logs/llama-server.log"
pkill -9 -f llama-server
sleep 3
rm -f /tmp/*.lock /tmp/llama* 2>/dev/null
# no-mmap ve mlock olmadan dene, warmup atla
nohup $BIN -m $MODEL --host 0.0.0.0 --port 8080 -ngl 99 -c 16384 -fa on -ctk q4_0 -ctv q4_0 --embeddings --metrics --no-warmup >> $LOG 2>&1 &
echo "PID $!"
for i in $(seq 1 120); do
    sleep 2
    r=$(curl -s --max-time 2 http://127.0.0.1:8080/health 2>/dev/null)
    echo "$r" | grep -q ok && echo "OK $((i*2))s" && exit 0
    echo "  ... $((i*2))s"
done
echo "TIMEOUT"
exit 1
