#!/bin/bash
# Walker'a hafızayı kullanan bir görev gönder, reranker log'unu izle
echo "=== Walker'a görev gönderiliyor ==="
curl -s -m 120 -X POST http://127.0.0.1:9002/task \
  -H 'Content-Type: application/json' \
  -d '{"task": "load_from_memory kullanarak VRAM ve llama-server hakkinda ne biliyorsun?"}' \
  2>&1 | python3 -m json.tool 2>/dev/null || cat
