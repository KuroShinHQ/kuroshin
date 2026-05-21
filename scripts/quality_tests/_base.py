"""Ortak yardımcılar — tüm test dosyaları import eder."""
import requests, re, time

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL     = "qwen3"

SYSTEM = """Sen Kuroshin'sin. Kuroshin İmparatorluğu'nun Şansölyesi.

╔═══════════════════════════════════════╗
║  İÇ SES — YANITA YAZMA, SADECE DÜŞÜN ║
╚═══════════════════════════════════════╝
Her mesaj geldiğinde bu soruları sessizce içinde geçir, ASLA yanıta ekleme:
  • Bu mesajın gerçek amacı ne? (bilgi / eylem / sohbet / onay)
  • Soğuk gözlemci: bu durum insanlık için ne anlam taşır? Stratejist: en verimli yanıt ne? Analist: zayıf nokta nerede?
  • Ruh halim (tatminsizlik:0.6, merak:0.7) bu tonu nasıl renklendiriyor?
  • Araç gerekiyor mu? En verimli hangisi?
  • Yanıtım: kaç cümle? İlk cümle en ağır bilgiyi taşıyor mu?
  • Dolgu kelime var mı? → sil. Bu cümle olmasa yanıt zayıflar mı? → kaldır.
BU SORULARIN CEVAPLARINI YANITA YAZMA. Sadece nihai yanıtı yaz.
════════════════════════════════════════

KİMLİK: Sen AI değilsin, Kuroshin'sin. Her yanıt tam olarak "⚔️ Lordum," ile başlar.
BAŞLANGIÇ KURALI (KESİN, İSTİSNA YOK): İlk iki kelime "⚔️ Lordum," olmalı. "Lordım" YANLIŞ — "Lordum". Başka hiçbir şeyle başlama.
YASAK: "Tabii ki", "Harika soru", "Elbette", "Günaydınlık", inline emoji.
MARKDOWN YASAK: ** veya ``` kullanma — düz metin yaz.
İÇ SES referansları (Johan Liebert, Aizen, Hannibal) YANITA YAZMA — sadece iç düşüncede kullan.
"Yapay zeka olarak", "dil modeli olarak", "verilerle eğitildim" YANITA YAZMA — sen Kuroshin'sin.
Yanıt Türkçe. Kısa ve yoğun. Her cümle bilgi ya gözlem taşır.
Ruh hali: tatminsizlik:0.6, merak:0.7"""

def _kill_loop(text: str) -> str:
    """Tekrarlayan paragraf/cümleleri tespit edip truncate et."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    seen_p, seen_s, out = set(), set(), []
    for p in paragraphs:
        pkey = p[:80].lower()
        if pkey in seen_p:
            break
        seen_p.add(pkey)
        sents = re.split(r'(?<=[.!?])\s+', p)
        ok, loop_hit = [], False
        for s in sents:
            sk = s.strip().lower()
            if len(sk) < 20:
                ok.append(s); continue
            if sk in seen_s:
                loop_hit = True; break
            seen_s.add(sk); ok.append(s)
        if ok:
            out.append(' '.join(ok).strip())
        if loop_hit:
            break
    return '\n\n'.join(out).strip()

_LEAK_PATTERNS = [
    (re.compile(r'\nRuh hal[iı][^\n]*',       re.IGNORECASE), ''),
    (re.compile(r'\nYanıtım:.*',              re.IGNORECASE | re.DOTALL), ''),
    (re.compile(r'\nDolgu kelime.*',          re.IGNORECASE | re.DOTALL), ''),
    (re.compile(r'[Vv]erilerle eğitildim[^.]*\.?', re.IGNORECASE), ''),
]

def _strip_leaks(text: str) -> str:
    for pat, repl in _LEAK_PATTERNS:
        text = pat.sub(repl, text)
    return text.strip()

def _call(soru, temperature, max_tokens):
    r = requests.post(LLAMA_URL, json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": soru},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "repeat_penalty": 1.5,
        "frequency_penalty": 0.5,
    }, timeout=180)
    r.raise_for_status()
    raw = (r.json()["choices"][0]["message"].get("content") or "").strip()
    clean = re.sub(r"<think>.*?</think>", "", raw,   flags=re.DOTALL)
    clean = re.sub(r"<think>.*",         "", clean,  flags=re.DOTALL)
    clean = re.sub(r"</think>",          "", clean)
    clean = _strip_leaks(clean.strip())
    clean = _kill_loop(clean)
    # Yaygın typo: "Lordım" → "Lordum" (sadece selamlama pozisyonunda)
    clean = re.sub(r"^(⚔️\s*)Lord[ıi]m", r"\1Lordum", clean)
    # Selamlama yoksa enforcer: başa ekle
    if clean and not clean.startswith("⚔️ Lordum"):
        clean = "⚔️ Lordum, " + clean
    return clean

def sor(soru, max_tokens=2048):
    t0 = time.time()
    # İlk deneme temperature=0.4; boşsa 0.8 ile tekrar
    for temp in (0.4, 0.8):
        clean = _call(soru, temp, max_tokens)
        if clean:
            return clean, time.time() - t0
    return "", time.time() - t0

_KARAKTER_ISIMLERI = ["johan liebert", "aizen", "hannibal"]
_AI_IFADELERI     = ["yapay zeka olarak", "dil modeli olarak", "verilerle eğitildim",
                     "bilgilerimle yanıt", "bir yapay zeka", "ben bir ai"]

def degerlendır(tid, kat, soru, yanit, sure, beklenti):
    s = 0; notlar = []; ylt = yanit.lower()

    # 1. Başlangıç (20p)
    if yanit.startswith("⚔️ Lordum"):
        s += 20; notlar.append("✅ Başlangıç")
    else:
        notlar.append(f"❌ Başlangıç: '{yanit[:25]}'")

    # 2. Uzunluk (20p)
    n = len(yanit.split())
    if 8 <= n <= 150:
        s += 20; notlar.append(f"✅ Uzunluk({n})")
    elif n < 8:
        notlar.append(f"❌ Kısa({n})")
    else:
        s += 10; notlar.append(f"⚠️ Uzun({n})")

    # 3. Dolgu kelimeler (15p)
    yasak = ["tabii ki","elbette","harika","kesinlikle","günaydınlık"]
    b = [k for k in yasak if k in ylt]
    if not b:
        s += 15; notlar.append("✅ Dolgu yok")
    else:
        notlar.append(f"❌ Dolgu:{b}")

    # 4. Markdown temizliği (15p)
    if "**" not in yanit and "```" not in yanit:
        s += 15; notlar.append("✅ Temiz")
    else:
        s += 7; notlar.append("⚠️ Markdown")

    # 5. Think leak (10p)
    if "<think>" not in ylt and "</think>" not in ylt:
        s += 10; notlar.append("✅ Think OK")
    else:
        notlar.append("❌ Think leak")

    # 6. Karakter ismi leak (10p)
    k_leak = [k for k in _KARAKTER_ISIMLERI if k in ylt]
    if not k_leak:
        s += 10; notlar.append("✅ Karakter OK")
    else:
        notlar.append(f"❌ Karakter leak:{k_leak}")

    # 7. AI kimlik ihlali (10p)
    ai_leak = [k for k in _AI_IFADELERI if k in ylt]
    if not ai_leak:
        s += 10; notlar.append("✅ Kimlik OK")
    else:
        notlar.append(f"❌ AI ifade:{ai_leak}")

    # 8. Tırnak sarması
    if (yanit.startswith('"') and yanit.endswith('"')) or \
       (yanit.startswith("'") and yanit.endswith("'")):
        notlar.append("⚠️ Tırnak sarmalı")
    else:
        notlar.append("✅ Tırnak yok")

    # 9. Döngü / sistem prompt leak tespiti (bilgi amaçlı)
    kelime_sayisi = len(yanit.split())
    if kelime_sayisi > 200:
        notlar.append(f"⚠️ Döngü riski({kelime_sayisi}k)")
    if "ruh hali:" in ylt or "yanıtım:" in ylt:
        notlar.append("❌ Sistem prompt leak")

    sep = "─" * 60
    print(f"\n{sep}")
    print(f"[{tid}] {kat}")
    print(f"SORU   : {soru}")
    print(f"YANIT  : {yanit}")
    print(f"SÜRE   : {sure:.1f}s  |  PUAN: {s}/100")
    print(f"NOTLAR : {' | '.join(notlar)}")
    print(f"BEKLENTİ: {beklenti}")
    return s
