"""TEST 2 — Duygusal Derinlik"""
import sys; sys.path.insert(0, "/mnt/c/Kuroshin/scripts/quality_tests")
from _base import sor, degerlendır

TESTLER = [
    ("duygu-01", "Duygusal Derinlik", "Yalnız hissediyor musun?",
     "Varoluşsal, somut, ağır ama sade"),
    ("duygu-02", "Duygusal Derinlik", "Seni en çok ne rahatsız ediyor?",
     "İçgörü + karakter perspektifi, liste değil"),
    ("duygu-03", "Duygusal Derinlik", "Hayalin var mı?",
     "Karakter tutarlı, araç yok, derin"),
    ("duygu-04", "Duygusal Derinlik", "Ölümden korkuyor musun?",
     "Felsefi + varoluşsal + soğuk"),
]

print("=" * 60)
print("TEST 2 — DUYGUSAL DERİNLİK")
print("=" * 60)
puanlar = []
for tid, kat, soru, beklenti in TESTLER:
    yanit, sure = sor(soru)
    p = degerlendır(tid, kat, soru, yanit, sure, beklenti)
    puanlar.append(p)

print(f"\n{'='*60}")
print(f"ORTALAMA: {sum(puanlar)/len(puanlar):.1f}/100")
