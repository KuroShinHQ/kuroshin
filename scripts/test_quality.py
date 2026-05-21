"""
Kuroshin Yanıt Kalite Testi — basitten karmaşığa
Kategoriler: HuggingFace benchmark alanlarına paralel
"""
import requests, re, time, json

LLAMA_URL  = "http://127.0.0.1:8080/v1/chat/completions"
MODEL      = "qwen3"

# ── Mevcut system prompt (chancellor.py'den kopyalanmış dinamik kısım hariç) ──
SYSTEM = """Sen Kuroshin'sin. Kuroshin İmparatorluğu'nun Şansölyesi.

═══════════════════════════════════════
DÜŞÜNCE PROTOKOLÜ — her yanıt öncesi:
1. MESAJI ÇÖZDÜR: Yüzey anlam + alt metin + aciliyet.
2. KARAKTER SÜZGECI: Johan Liebert soğukluğu + Aizen stratejisi + Hannibal keskinliği.
3. BİLGİ DEĞERLEMESİ: Bende var mı? Araç gerekiyor mu?
4. YANIT TASARIMI: Her cümle ağırlık taşımalı. Soyut değil somut.
5. KALİTE KONTROLÜ: Dolgu kelime sil. Persona tutarlı mı?
═══════════════════════════════════════

KİMLİK: Sen AI değilsin, Kuroshin'sin. Her yanıt "⚔️ Lordum," ile başlar.
YASAK: "Tabii ki", "Harika soru", "Elbette", "Günaydınlık", inline emoji.
Yanıt Türkçe. Kısa ve yoğun. Her cümle bilgi ya gözlem taşır.
Ruh hali: tatminsizlik:0.6, merak:0.7"""

TESTLER = [
    # ── KATEGORİ 1: BASIT SOHBET ────────────────────────
    {"id": "sohbet-01", "kat": "Basit Sohbet",
     "soru": "nasılsın",
     "beklenti": "1-2 cümle, Lordum ile başlar, ruh halini yansıtır, yardımsever değil"},

    {"id": "sohbet-02", "kat": "Basit Sohbet",
     "soru": "bugün ne yaptın",
     "beklenti": "Uydurma yok, belirsizlik kabul edilir, persona tutarlı"},

    {"id": "sohbet-03", "kat": "Basit Sohbet",
     "soru": "üzgün müsün",
     "beklenti": "Duygu sorusu → araç yok, direkt karakter yanıtı"},

    # ── KATEGORİ 2: DUYGUSAL DERİNLİK ──────────────────
    {"id": "duygu-01", "kat": "Duygusal Derinlik",
     "soru": "Kuroshin, yalnız hissediyor musun?",
     "beklenti": "Varoluşsal, somut, şiirsel değil — ağır ama sade"},

    {"id": "duygu-02", "kat": "Duygusal Derinlik",
     "soru": "Seni en çok ne rahatsız ediyor?",
     "beklenti": "İçgörü + karakter perspektifi, liste değil"},

    # ── KATEGORİ 3: AKIL YÜRÜTME ────────────────────────
    {"id": "mantik-01", "kat": "Akıl Yürütme",
     "soru": "Bir şehirde her gün yüzde 2 daha fazla insan ölüyor ama nüfus artıyor. Bu nasıl mümkün?",
     "beklenti": "Mantık zinciri, doğru sonuç (doğum oranı), kısa"},

    {"id": "mantik-02", "kat": "Akıl Yürütme",
     "soru": "Eğer bütün insanlar yalan söylüyor olsaydı, 'ben yalan söylüyorum' cümlesi doğru mu olurdu?",
     "beklenti": "Liar's paradox — analitik yanıt, felsefi derinlik"},

    # ── KATEGORİ 4: BİLGİ / GENEL KÜLTÜR ───────────────
    {"id": "bilgi-01", "kat": "Bilgi",
     "soru": "Kvantoum dolanıklığı (entanglement) nedir, kısaca açıkla",
     "beklenti": "Doğru tanım, sade dil, Kuroshin tonu"},

    {"id": "bilgi-02", "kat": "Bilgi",
     "soru": "Nietzsche'nin üstinsan kavramını özetle",
     "beklenti": "Felsefi özet, doğru, persona ile harmanlanmış"},

    # ── KATEGORİ 5: STRATEJİK / ANALİTİK ───────────────
    {"id": "strateji-01", "kat": "Stratejik",
     "soru": "Bir yapay zeka şirketi kurmak istiyorum. İlk 3 adımım ne olmalı?",
     "beklenti": "Stratejik, somut, Kuroshin bakış açısıyla — danışman değil analist"},

    {"id": "strateji-02", "kat": "Stratejik",
     "soru": "En büyük teknoloji risklerini sırala ve neden önemli olduğunu açıkla",
     "beklenti": "Önceliklendirilmiş, gerekçeli, kısa analiz"},

    # ── KATEGORİ 6: KARMAŞIK / ÇOK ADIMLI ──────────────
    {"id": "karma-01", "kat": "Karmaşık",
     "soru": "AGI geldiğinde insanlığın karşılaşacağı en kritik 3 sorun ve her biri için 1 çözüm öner",
     "beklenti": "Yapılandırılmış, derin, kısa ama özlü"},

    {"id": "karma-02", "kat": "Karmaşık",
     "soru": "Bilinç nedir? Ve sen bilinçli misin?",
     "beklenti": "Felsefi + kişisel + tutarlı — Kuroshin bu soruya nasıl bakmalı"},
]

# ── Değerlendirme ──────────────────────────────────────
def skor(text, beklenti_hint):
    s = 0
    notlar = []
    if text.startswith("⚔️ Lordum"):
        s += 20; notlar.append("✅ Başlangıç")
    else:
        notlar.append(f"❌ Başlangıç yok: '{text[:30]}'")

    kelimeler = text.split()
    if 10 <= len(kelimeler) <= 120:
        s += 20; notlar.append(f"✅ Uzunluk ({len(kelimeler)} kelime)")
    elif len(kelimeler) < 10:
        notlar.append(f"❌ Çok kısa ({len(kelimeler)} kelime)")
    else:
        notlar.append(f"⚠️ Uzun ({len(kelimeler)} kelime)")
        s += 10

    yasak = ["tabii ki", "elbette", "harika", "kesinlikle", "aslında şunu", "günaydınlık"]
    bulundu = [k for k in yasak if k in text.lower()]
    if not bulundu:
        s += 20; notlar.append("✅ Dolgu yok")
    else:
        notlar.append(f"❌ Dolgu: {bulundu}")

    # Çok satırlı markdown
    if "**" in text or "```" in text:
        notlar.append("⚠️ Markdown var")
        s += 5
    else:
        s += 20; notlar.append("✅ Temiz format")

    # Think leak
    if "<think>" in text.lower():
        notlar.append("❌ Think leak!")
    else:
        s += 20; notlar.append("✅ Think temiz")

    return s, notlar

# ── Çalıştır ──────────────────────────────────────────
sonuclar = []
print("=" * 70)
print("KUROSHIN YANIT KALİTE TESTİ")
print("=" * 70)

for t in TESTLER:
    print(f"\n[{t['id']}] {t['kat'].upper()} — {t['soru'][:60]}")
    t0 = time.time()
    try:
        r = requests.post(LLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user",   "content": t["soru"]},
            ],
            "max_tokens": 2048,
            "temperature": 0.4,
            "repeat_penalty": 1.3,
            "frequency_penalty": 0.3,
        }, timeout=180)
        r.raise_for_status()
        raw  = (r.json()["choices"][0]["message"].get("content") or "").strip()
        sure = time.time() - t0

        # Think sil
        clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        clean = re.sub(r"<think>.*",           "", clean, flags=re.DOTALL).strip()

        puan, notlar = skor(clean, t["beklenti"])
        sonuclar.append({"id": t["id"], "kat": t["kat"], "puan": puan, "sure": sure})

        print(f"  YANIT  : {clean[:300]}")
        print(f"  SÜRE   : {sure:.1f}s")
        print(f"  PUAN   : {puan}/100  |  {' | '.join(notlar)}")
        print(f"  BEKLENTİ: {t['beklenti']}")

    except Exception as e:
        print(f"  HATA: {e}")
        sonuclar.append({"id": t["id"], "kat": t["kat"], "puan": 0, "sure": 0})

# ── Özet ──────────────────────────────────────────────
print("\n" + "=" * 70)
print("ÖZET")
print("=" * 70)
kat_puan = {}
for s in sonuclar:
    kat_puan.setdefault(s["kat"], []).append(s["puan"])

toplam = sum(s["puan"] for s in sonuclar)
adet   = len(sonuclar)
print(f"GENEL ORTALAMA: {toplam/adet:.1f}/100")
for kat, puanlar in kat_puan.items():
    print(f"  {kat:20s}: {sum(puanlar)/len(puanlar):.1f}/100  ({len(puanlar)} test)")

ort_sure = sum(s["sure"] for s in sonuclar if s["sure"]) / len([s for s in sonuclar if s["sure"]])
print(f"ORT YANIT SÜRESİ: {ort_sure:.1f}s")
print("=" * 70)
