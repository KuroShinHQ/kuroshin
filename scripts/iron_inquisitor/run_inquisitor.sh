#!/bin/bash
# Iron Inquisitor v4.0 — WSL Başlatıcı
# Kullanım: bash run_inquisitor.sh [--eval-loop] [--auto-apply] [--cycles N]

source /root/kuroshin/venv/bin/activate

MODE=""
CYCLES=3
EXTRA_ARGS=""

for arg in "$@"; do
    case "$arg" in
        --eval-loop)  MODE="eval" ;;
        --auto-apply) EXTRA_ARGS="$EXTRA_ARGS --auto-apply" ;;
        --cycles)     shift; CYCLES="$1" ;;
    esac
done

if [ "$MODE" = "eval" ]; then
    echo "[INQUISITOR] Eval Feedback Loop başlatılıyor (cycles=$CYCLES)..."
    python3 /mnt/c/Kuroshin/scripts/iron_inquisitor/eval_feedback_loop.py --cycles $CYCLES $EXTRA_ARGS
else
    echo "[INQUISITOR] Tek seferlik test çalıştırılıyor..."
    python3 /mnt/c/Kuroshin/scripts/iron_inquisitor/inquisitor.py
fi
