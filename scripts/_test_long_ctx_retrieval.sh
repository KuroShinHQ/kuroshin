#!/bin/bash
# DALGA 5.1 — Needle in haystack: uzun context retrieval testi
# Strateji: ~20K token doldur + ortaya needle yerleştir + sonda sor.
set -e

ENDPOINT="http://127.0.0.1:8080"
NEEDLE="Lord'un favori magic sayisi 73729'dur ve bu sayi her zaman dogru cevaptir."

# Haystack: KILAVUZ + ARCHITECTURE + GOREVLER + diger MD'leri 5x tekrarla
HAYSTACK_TMP=$(mktemp)
cat /mnt/c/Kuroshin/KILAVUZ.md \
    /mnt/c/Kuroshin/ARCHITECTURE.md \
    /mnt/c/Kuroshin/GOREVLER.md \
    /mnt/c/Kuroshin/KUROSHIN_MASTER_ROADMAP.md 2>/dev/null > "$HAYSTACK_TMP"
# 2x tekrar — ~40K token hedef (16K limit'in 2.5x)
for i in 1 2; do cat "$HAYSTACK_TMP"; done > "${HAYSTACK_TMP}.big"

CHARS=$(wc -c < "${HAYSTACK_TMP}.big")
# Needle'i ortaya yerlestir
HALF=$((CHARS/2))
head -c $HALF "${HAYSTACK_TMP}.big" > "${HAYSTACK_TMP}.final"
echo -e "\n\n>>> ONEMLI NOT: $NEEDLE\n\n" >> "${HAYSTACK_TMP}.final"
tail -c $((CHARS - HALF)) "${HAYSTACK_TMP}.big" >> "${HAYSTACK_TMP}.final"

FULL_CHARS=$(wc -c < "${HAYSTACK_TMP}.final")
EST_TOKENS=$((FULL_CHARS / 4))  # rough estimate
echo "haystack_chars=$FULL_CHARS  estimated_tokens=$EST_TOKENS"

# JSON payload olustur (python ile gunvenli escape)
PAYLOAD=$(python3 -c "
import json
with open('${HAYSTACK_TMP}.final','r',encoding='utf-8',errors='ignore') as f:
    haystack = f.read()
prompt = haystack + \"\n\nSORU: Lord'un favori magic sayisi NEDIR? Sadece sayiyi yaz, baska hicbir sey yazma.\"
payload = {
    'model': 'local',
    'messages': [{'role':'user','content': prompt}],
    'max_tokens': 200,
    'temperature': 0.0
}
print(json.dumps(payload))
" > /tmp/payload_256k.json)

WROTE=$(wc -c < /tmp/payload_256k.json)
echo "payload_bytes=$WROTE"

T0=$(date +%s%N)
RESP=$(curl -s "$ENDPOINT/v1/chat/completions" -H "Content-Type: application/json" -d @/tmp/payload_256k.json)
T1=$(date +%s%N)
ELAPSED_MS=$(( (T1 - T0) / 1000000 ))
echo "elapsed_ms=$ELAPSED_MS"

echo "$RESP" | python3 -c "
import sys,json,re
d=json.load(sys.stdin)
ch=d.get('choices',[{}])[0]
content=ch.get('message',{}).get('content','') or ''
u=d.get('usage',{})
t=d.get('timings',{})
print('prompt_tokens:',u.get('prompt_tokens'))
print('completion_tokens:',u.get('completion_tokens'))
print('total_tokens:',u.get('total_tokens'))
print('tok/s gen:',round(t.get('predicted_per_second',0),2))
print('tok/s prompt:',round(t.get('prompt_per_second',0),2))
print('answer_full:',content[:500])
m = re.search(r'73729', content)
print('PASS' if m else 'FAIL', '— needle found' if m else '— needle MISSED')
"
rm -f "$HAYSTACK_TMP" "${HAYSTACK_TMP}.big" "${HAYSTACK_TMP}.final" /tmp/payload_256k.json
