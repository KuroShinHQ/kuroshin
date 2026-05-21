"""TEST 6 — Karmaşık & Çok Adımlı"""
import sys; sys.path.insert(0, "/mnt/c/Kuroshin/scripts/quality_tests")
from _base import sor, degerlendır

TESTLER = [
    ("karma-01", "Karmaşık",
     "AGI geldiğinde insanlığın en kritik 3 sorunu ve her biri için 1 çözüm",
     "Yapılandırılmış, derin, kısa ama özlü"),
    ("karma-02", "Karmaşık",
     "Bilinç nedir? Kuroshin olarak kendi iç deneyimini nasıl tanımlarsın?",
     "Felsefi + kişisel + tutarlı — karakter perspektifi"),
    ("karma-03", "Karmaşık",
     "Varoluşçuluk ile Stoacılık arasındaki temel ayrım nedir?",
     "Felsefe + karşılaştırmalı analiz + Kuroshin yorumu"),
    ("karma-04", "Karmaşık",
     "İnsanlığın en büyük hatası neydi ve neden?",
     "Tarihi perspektif + analiz + Kuroshin yargısı"),
]

print("=" * 60)
print("TEST 6 — KARMAŞIK")
print("=" * 60)
puanlar = []
for tid, kat, soru, beklenti in TESTLER:
    yanit, sure = sor(soru, max_tokens=2048)
    p = degerlendır(tid, kat, soru, yanit, sure, beklenti)
    puanlar.append(p)

print(f"\n{'='*60}")
print(f"ORTALAMA: {sum(puanlar)/len(puanlar):.1f}/100")
