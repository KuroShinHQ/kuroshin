#!/usr/bin/env python3
"""DALGA-6 FAZ-3 standalone test: analyze_flaws + evaluate_reviews + merchant_judge.

Lord direktifi: Iron Inquisitor offline + canlı kanıt zorunlu.
Bu script 3 sub-test koşar, her birinde llama-server JSON mode response_format=json_object
çıktısını doğrular.
"""
import sys, time, json
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_market_master import (
    analyze_flaws, evaluate_reviews, merchant_judge,
    ProductListing, KUSUR_RISK,
)

print(f"[FAZ-3 REASONING TEST] {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 72)

# ============================================================================
# Test 1: analyze_flaws (4 kusur tipi: kozmetik/kullanim/fonksiyonel/yapisal)
# ============================================================================
print("\n>>> TEST 1: analyze_flaws (3 ornek 2.el ilan)")
print("-" * 72)
FLAW_SAMPLES = [
    ("ufak çizik", "Sıfır ayarında, sadece ufak çizik var, etiketleri duruyor. Çalışıyor.", "kozmetik"),
    ("kullanim",   "Kabloda ezilme var, koltuk yıpranmış. Çalışmaya devam ediyor ama estetik bozuk.", "kullanim"),
    ("yapisal",    "Şase çatlağı tespit edildi, devre kartı yanık, garanti bitti.", "yapisal"),
]

t1_pass = 0
for label, desc, expected_type in FLAW_SAMPLES:
    t0 = time.time()
    result = analyze_flaws(desc)
    elapsed = round(time.time() - t0, 1)
    flaws = result.get("flaws", [])
    total = result.get("total_kesinti", 0)
    detected_types = [f.get("tip", "") for f in flaws]
    has_expected = expected_type in detected_types
    status = "✓" if has_expected else "✗"
    print(f"  {status} [{label}] elapsed={elapsed}s → flaws={len(flaws)} types={detected_types} total_kesinti={total}")
    if has_expected:
        t1_pass += 1

print(f"\n  TEST 1 SONUC: {t1_pass}/{len(FLAW_SAMPLES)} kusur tipi dogru tespit")

# ============================================================================
# Test 2: evaluate_reviews (Bayesian + kronik sorun)
# ============================================================================
print("\n>>> TEST 2: evaluate_reviews (kronik sorun cikari)")
print("-" * 72)
REVIEW_SAMPLES = [
    "Bisiklet harika, ancak motor zamanla ses yapıyor. 6 ay sonra fark ettim.",
    "Çok güzel ürün, kullanışlı. Sadece motoru biraz gürültülü çalışıyor.",
    "Kaliteli, sağlam yapı. Motor sesi rahatsız etti ama dayanıyor.",
    "Mükemmel! Tek sıkıntı motorun bazen titremesi.",
    "Aldığım için çok memnunum. Motor sesi ufak bir kusur ama yine de iyi.",
    "Tavsiye ederim. Sadece motor zamanla ses yapmaya başladı.",
]

t0 = time.time()
result = evaluate_reviews(REVIEW_SAMPLES)
elapsed = round(time.time() - t0, 1)
kronik = result.get("kronik_sorunlar", [])
ozet = result.get("ozet", "")
print(f"  Sonuc: kronik_sorun_n={len(kronik)} elapsed={elapsed}s")
print(f"  Ozet: {ozet[:150]}")
for ks in kronik[:3]:
    print(f"    - {ks.get('sorun', '?')} (frekans={ks.get('frekans', '?')})")
t2_pass = 1 if kronik else 0  # En az 1 kronik sorun (motor sesi)

# ============================================================================
# Test 3: merchant_judge (V/R/F + LLM JSON mode → final gerekce)
# ============================================================================
print("\n>>> TEST 3: merchant_judge (final karar gerekce)")
print("-" * 72)
test_listing = ProductListing(
    title="XYZ ProSpin 5000 Manyetik Kondisyon Bisikleti",
    price=4799.0,
    url="https://www.epey.com/kondisyon-bisikleti/test-urun.html",
    site="epey",
    rating=4.65,
    review_count=1234,
    description="14 kg volan, manyetik direnç, taşıma kapasitesi 130 kg, kalp sensörü yok, katlanabilir değil.",
    features={"volan_kg": "14", "tasima_kg": "130", "direnc": "manyetik"},
    is_second_hand=False,
)
test_listing.v_score = 9.5
test_listing.r_score = 9.0
test_listing.f_score = 9.0
test_listing.master_score = 9.2

criteria = {"kritik": ["volan agirligi", "manyetik direnc", "tasima kapasitesi", "sele ayar"]}
t0 = time.time()
result = merchant_judge(test_listing, criteria, mod="dengeli")
elapsed = round(time.time() - t0, 1)
gerekce = result.get("gerekce", "")
final = result.get("final_score", 0)
print(f"  Sonuc: final_score={final} elapsed={elapsed}s")
print(f"  Gerekce: {gerekce[:300]}")
t3_pass = 1 if (gerekce and len(gerekce) > 20 and final > 0) else 0

# ============================================================================
print("\n" + "=" * 72)
toplam_pass = t1_pass + t2_pass + t3_pass
toplam = len(FLAW_SAMPLES) + 1 + 1  # 3 + 1 + 1 = 5
print(f"[FAZ-3 SONUC] {toplam_pass}/{toplam} test PASS")
print(f"  T1 analyze_flaws:     {t1_pass}/{len(FLAW_SAMPLES)}")
print(f"  T2 evaluate_reviews:  {t2_pass}/1")
print(f"  T3 merchant_judge:    {t3_pass}/1")
sys.exit(0 if toplam_pass >= 3 else 1)
