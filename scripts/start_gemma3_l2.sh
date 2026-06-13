#!/bin/bash
# Gemma 3 4B-IT L2 — TurboQuant, HOME=/tmp router mode bypass, -np 1
exec env HOME=/tmp /opt/llama-turboquant/bin/llama-server \
  --model "/mnt/c/Kuroshin/kuroshin-downloads/gemma-3-4b-it-Q4_K_M.gguf" \
  --port 8082 \
  --host 0.0.0.0 \
  --ctx-size 4096 \
  -np 1 \
  --cache-type-k tq3_0 \
  --cache-type-v tq3_0 \
  --no-warmup \
  >> /tmp/llama_gemma3.log 2>&1
