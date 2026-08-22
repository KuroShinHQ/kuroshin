#!/bin/bash
# Llama-server başlatıcı — active_model.json'dan dinamik model okur
# SYSTEM_PAUSED.flag check (Lord direktifi 2 Haz 2026)
source /mnt/c/KuroshinHQ/_hub/shared-scripts/_check_system_paused.sh
source /mnt/c/KuroshinHQ/_hub/shared-scripts/kuro_logger.sh "/mnt/c/KuroshinHQ/_hub/shared-logs/start_llama_launcher.log"
klog_header "start_llama.sh"
STATE_FILE="/mnt/c/KuroshinHQ/_hub/shared-memory/active_model.json"
BIN="/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
LAGUNA_BIN="/root/kuroshin/engines/laguna.cpp/build/bin/llama-server"
LOG="/mnt/c/KuroshinHQ/_hub/shared-logs/llama-server.log"
FALLBACK_CTX=32768
DFLASH="/mnt/c/KuroshinHQ/_hub/models/laguna-s-2.1-DFlash-BF16.gguf"

# active_model.json'dan model yolu ve context oku
if [ -f "$STATE_FILE" ]; then
    MODEL=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('path',''))" 2>/dev/null)
    CTX=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('context_size','') or '')" 2>/dev/null)
fi

# Model yoksa HATA — fallback YOK (tek model politikasi: 30B Qwen, 2 Agustos 2026)
if [ -z "$MODEL" ] || [ ! -f "$MODEL" ]; then
    klog ERROR "Aktif model bulunamadi: $MODEL (active_model.json kontrol edin)"
    echo "HATA: model bulunamadi: $MODEL"
    klog_exit 1 "llama-server"
    exit 1
fi
[ -z "$CTX" ] && CTX=$FALLBACK_CTX

MODEL_NAME=$(basename "$MODEL")
klog INFO "Model: $MODEL_NAME (ctx=$CTX)"

# MoE tespiti: isimde a3b, moe, -ax veya laguna varsa MoE
is_moe=0
echo "$MODEL_NAME" | grep -qiE '(a3b|moe|-ax|laguna)' && is_moe=1

# Laguna tespiti: isimde laguna varsa Laguna fork + DFlash + jinja
is_laguna=0
echo "$MODEL_NAME" | grep -qiE 'laguna' && is_laguna=1
if [ $is_laguna -eq 1 ]; then
    BIN="$LAGUNA_BIN"
    klog INFO "Laguna modu: laguna.cpp binary + --jinja"
fi

# Reasoning model tespiti: isimde deepseek, r1, thinking, veya reasoning varsa
is_reasoning=0
echo "$MODEL_NAME" | grep -qiE '(deepseek|r1|thinking|reasoning|qwen3\.8|qwen38)' && is_reasoning=1

# Qwen3.8 tespiti: natif MTP tensörleri (draft-mtp spekülatif decoding)
is_qwen38=0
echo "$MODEL_NAME" | grep -qiE 'qwen3\.8|qwen38' && is_qwen38=1

# Qwen3.5-9B tespiti: 256K context icin KV CPU'ya (-nkvo) + tam GPU offload
is_qwen9b=0
echo "$MODEL_NAME" | grep -qiE 'qwen3\.5-9b|qwen35-9b' && is_qwen9b=1

# Qwen3.5-35B-A3B tespiti: MoE + vision (mmproj) destegi
is_35b_a3b=0
echo "$MODEL_NAME" | grep -qiE '35b-a3b|35ba3b' && is_35b_a3b=1

if [ $is_moe -eq 1 ]; then
    # --reasoning-budget: think bloğunu 2K ile sınırla (FAZ B 1 Haz 2026: 3072→2048 %33 hız)
    EXTRA_PARAMS='-ot "exps=CPU" --reasoning-budget 2048'
    klog INFO "MoE modu: expert'ler CPU'ya alınıyor (reasoning-budget=2048)"
elif [ $is_qwen38 -eq 1 ]; then
    # Qwen3.8-27B: natif MTP — ayrı draft modeli yok, tensörler ağırlığın içinde
    EXTRA_PARAMS="--spec-default --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-type-k q8_0 --spec-draft-type-v q8_0 --reasoning-budget 2048"
    klog INFO "Qwen3.8 modu: draft-mtp (n-max 2) + q8_0 draft KV + reasoning-budget 2048"
else
    # build 10507: --draft-max kaldirildi -> --spec-ngram-mod-n-max
    EXTRA_PARAMS="--spec-type ngram-cache --spec-ngram-mod-n-max 16 --spec-ngram-mod-n-min 2 --spec-draft-p-min 0.7"
    klog INFO "Dense modu: speculative decoding aktif (ngram-mod, build 10507)"
    if [ $is_reasoning -eq 1 ]; then
        EXTRA_PARAMS="$EXTRA_PARAMS --reasoning-budget 2048"
        klog INFO "Reasoning model tespiti: --reasoning-budget 2048 parametresi eklendi"
    fi
fi

pkill -9 -f llama-server 2>/dev/null
sleep 1

JINJA_FLAG=""
{ [ $is_laguna -eq 1 ] || [ $is_qwen38 -eq 1 ] || [ $is_35b_a3b -eq 1 ]; } && JINJA_FLAG="--jinja"

# Qwen3.8-27B: 8GB VRAM icin 25 GPU katman sabit (19 Ağustos 2026 benchmark)
# Prefill 150 t/s + decode ~4 t/s + MTP %49 kabul, VRAM 7.87GB (tasma yok)
NGL_FLAG="-ngl 99"
EXTRA_BATCH=""
if [ $is_qwen38 -eq 1 ]; then
    NGL_FLAG="-ngl 25"
    EXTRA_BATCH="-t 6 -b 512 -ub 512"
    # Unsloth IQ4_XS'te result_norm/result_embd YOK -> --embeddings GGML_ASSERT crash
    klog INFO "Qwen3.8 modu: 25 katman GPU + P-core thread + embeddings KAPALI"
fi
if [ $is_qwen9b -eq 1 ]; then
    # 256K context: KV CPU'da (q4_0 ~5.4GB RAM) -> GPU'da weights tam (5GB)
    NGL_FLAG="-ngl 99"
    EXTRA_BATCH="-t 8 -nkvo"
    klog INFO "Qwen3.5-9B modu: tam GPU + 256K KV CPU'da (-nkvo)"
fi

MMPROJ_FLAG=""
if [ $is_35b_a3b -eq 1 ]; then
    # Vision: mmproj dosyasi model ile ayni dizinde (f16)
    MMPROJ_FILE="/mnt/c/KuroshinHQ/_hub/models/mmproj-Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf"
    if [ -f "$MMPROJ_FILE" ]; then
        MMPROJ_FLAG="--mmproj $MMPROJ_FILE"
        klog INFO "Qwen3.5-35B-A3B modu: vision (mmproj) AKTIF"
    else
        klog WARN "mmproj bulunamadi: $MMPROJ_FILE — vision kapali"
    fi
fi

DFLASH_FLAG=""
# Not: IQ1_S'ta result_norm/result_embd tensor eksik → GGML_ASSERT crash
# DFlash icin daha yuksek kaliteli quant (IQ4_XS+) gerekli
[ $is_laguna -eq 1 ] && [ -f "$DFLASH" ] && DFLASH_FLAG="-md $DFLASH --spec-type draft-dflash --spec-draft-n-max 15"

EMBED_FLAG="--embeddings"
[ $is_qwen38 -eq 1 ] && EMBED_FLAG=""
[ $is_35b_a3b -eq 1 ] && EMBED_FLAG=""

eval nohup "$BIN" -m "$MODEL" \
    --host 0.0.0.0 --port 8080 \
    $NGL_FLAG -c "$CTX" -fa on \
    -ctk q4_0 -ctv q4_0 \
    $EMBED_FLAG --mlock --no-mmap \
    --metrics \
    $EXTRA_BATCH \
    $JINJA_FLAG $DFLASH_FLAG $MMPROJ_FLAG \
    $EXTRA_PARAMS \
    >> "$LOG" 2>&1 &

echo "llama-server PID $! baslatildi, 8080 portu bekleniyor..."
klog INFO "llama-server PID $! baslatildi (port 8080)"

# FIX-ALL A1 (3 Haz 2026): 35B+256K ctx ~150s normal, timeout 90s → 240s
# FIX A-1 (2 Agustos 2026): Qwen3-Coder-30B 16.45GB + 8GB VRAM init 240-300s'yi asiyor → timeout 240s → 600s
# Lord direktifi: timer sürekli görünsün, sessiz kalmasın
for i in $(seq 1 300); do
    sleep 2
    if curl -s --max-time 2 http://127.0.0.1:8080/health | grep -q ok; then
        echo "llama-server HAZIR ($((i*2))s)"
        klog PASS "llama-server HAZIR ($((i*2))s)"
        klog_exit 0 "llama-server"
        exit 0
    fi
    # Her 20s'de bir progress (10 iter)
    if [ $((i % 10)) -eq 0 ]; then
        echo "  ... llama-server yukleniyor ($((i*2))s gecti, max 600s)"
        klog INFO "llama-server yukleniyor ($((i*2))s / max 600s)"
    fi
done
echo "UYARI: 600s icinde yanit yok (30B+8GB VRAM agir offload, bat ana akıştan devam)"
klog WARN "600s icinde yanit yok (bat ana akistan devam)"
klog_exit 1 "llama-server"
exit 1
