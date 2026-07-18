#!/bin/bash
for i in $(seq 1 60); do
    sleep 2
    r=$(curl -s --max-time 2 http://127.0.0.1:8080/health 2>/dev/null)
    if echo "$r" | grep -q ok; then
        echo "OK $((i*2))s"
        exit 0
    fi
done
echo "TIMEOUT"
exit 1
