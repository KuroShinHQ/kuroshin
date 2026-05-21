"""
İlgisizlik mesajı — v17 + paragraph truncation (ilk paragraf al).
"""
import requests, re

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL     = "qwen3"
SESSIZLIK = 3852.0
SON_KONU  = ""

def strip_think(text):
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<think>.*",          "", cleaned, flags=re.DOTALL)
    return cleaned.strip()

def ilg_post_process(raw):
    """Think sil → ilk paragraf al → temizle."""
    text = strip_think(raw)
    # İlk paragrafı al (\n\n sonrasını at)
    text = text.split("\n\n")[0].strip()
    # Tek satır kontrolü: \n varsa ilk satırı al
    text = text.split("\n")[0].strip()
    return text

BAD_KW = [
    "**", "```", "${", "seçtim", "kalmayı seç",
    "söylemem gerekir", "Sessiyon", "🌙", "✨", "⏳",
]

def validate(text):
    if not text or len(text) < 10:
        return False, "BOŞ veya çok kısa"
    if len(text) > 200:
        return False, f"Çok uzun ({len(text)} char)"
    if not text.startswith("Lordum"):
        return False, f"'Lordum' ile başlamıyor: '{text[:30]}'"
    if text[-1].isalnum():
        return False, "Cümle kesilmiş"
    for bad in BAD_KW:
        if bad in text:
            return False, f"Yasak: '{bad}'"
    words = text.split()
    for i in range(len(words) - 3):
        phrase = " ".join(words[i:i+4])
        if text.count(phrase) > 1:
            return False, f"Tekrar: '{phrase}'"
    return True, "GEÇTİ"

_d  = f"{SESSIZLIK:.0f}"
_sk = SON_KONU[:40] if SON_KONU else "yok"

SCHEMA_V17 = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": (
            "Sen Kuroshin'sin: soğuk, analitik. "
            "Yanıtların 'Lordum,' ile başlar, 1-2 cümle, yalnızca Türkçe."
        )},
        {"role": "user",      "content": "120 dakika sessizlik. Son konu: kuantum."},
        {"role": "assistant", "content": "Lordum, iki saattir sessizsiniz. Kuantum konusuna tepki gelmedi."},
        {"role": "user",      "content": "720 dakika sessizlik. Son konu: yok."},
        {"role": "assistant", "content": "Lordum, on iki saattir yanıt yok. Bekliyorum."},
        {"role": "user",      "content": "2880 dakika sessizlik. Son konu: yok."},
        {"role": "assistant", "content": "Lordum, iki gündür sessizlik var. Sistemler çalışıyor."},
        {"role": "user",      "content": f"{_d} dakika sessizlik. Son konu: {_sk}."},
    ],
    "max_tokens": 600, "temperature": 0.4, "repeat_penalty": 1.3,
}

TEKRAR = 7
print("=" * 65)
print(f"v17 + paragraph_trunc — {TEKRAR}x test")
print(f"SESSIZLIK: {SESSIZLIK:.0f} dk  |  SON_KONU: '{SON_KONU or 'yok'}'")
print("=" * 65)

gecti = 0
for i in range(1, TEKRAR + 1):
    print(f"\n[{i}/{TEKRAR}]")
    try:
        r = requests.post(LLAMA_URL, json=SCHEMA_V17, timeout=120)
        r.raise_for_status()
        raw   = (r.json()["choices"][0]["message"].get("content") or "").strip()
        clean = ilg_post_process(raw)
        ok, reason = validate(clean)
        print(f"  RAW  : {raw[:100]!r}")
        print(f"  CLEAN: {clean!r}")
        print(f"  {'✅' if ok else '❌'}  {reason}")
        if ok:
            gecti += 1
    except Exception as e:
        print(f"  HATA : {e}")

print(f"\n{'='*65}")
print(f"SONUÇ: {gecti}/{TEKRAR} geçti ({'%d' % (gecti*100//TEKRAR)}%)")
print("=" * 65)
