#!/bin/bash
for i in $(seq 1 90); do
    sleep 2
    r=$(curl -s --max-time 3 http://127.0.0.1:8080/health 2>/dev/null)
    if echo "$r" | grep -q ok; then
        echo "OK $((i*2))s"
        exit 0
    fi
    echo "bekle... $((i*2))s"
done
echo "TIMEOUT"
exit 1
