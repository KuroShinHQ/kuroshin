#!/bin/bash
# E-16 (29 May 2026): Qwen3-30B-A3B-Instruct-2507 IQ4_XS indirme
cd /root/kuroshin/models || exit 1
LOG=/root/kuroshin/logs/qwen3_2507_dl.log
mkdir -p /root/kuroshin/logs
echo "[$(date)] E-16 indirme baslatildi" > "$LOG"
wget -c --progress=dot:giga \
  -O Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated.i1-IQ4_XS.gguf \
  'https://huggingface.co/mradermacher/Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated-i1-GGUF/resolve/main/Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated.i1-IQ4_XS.gguf' \
  >> "$LOG" 2>&1
EXIT=$?
echo "[$(date)] Cikis kodu: $EXIT" >> "$LOG"
ls -lah Huihui-Qwen3-30B*.gguf >> "$LOG" 2>&1
exit $EXIT
