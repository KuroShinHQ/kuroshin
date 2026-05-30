#!/bin/bash
# DALGA 5.1 — 256K context probe
set -e

ENDPOINT="http://127.0.0.1:8080"

echo "=== props.n_ctx ==="
curl -s "$ENDPOINT/props" | python3 -c "import sys,json;d=json.load(sys.stdin);print('n_ctx=',d.get('default_generation_settings',{}).get('n_ctx',d.get('n_ctx','?')))"

echo
echo "=== short prompt latency ==="
T0=$(date +%s%N)
RESP=$(curl -s "$ENDPOINT/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"local","messages":[{"role":"user","content":"Sadece SAYI cevap ver: 2+2 kac?"}],"max_tokens":40,"temperature":0.0}')
T1=$(date +%s%N)
ELAPSED_MS=$(( (T1 - T0) / 1000000 ))
echo "elapsed_ms=$ELAPSED_MS"
echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ch=d.get('choices',[{}])[0]
msg=ch.get('message',{})
content=msg.get('content','')
think=msg.get('reasoning_content','')
print('content_preview:',(content or '')[:200])
print('think_preview:',(think or '')[:120])
u=d.get('usage',{})
t=d.get('timings',{})
print('usage:',u)
print('tok/s gen:',t.get('predicted_per_second','?'))
print('tok/s prompt:',t.get('prompt_per_second','?'))
"
