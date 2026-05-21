"""TEST 1 — Basit Sohbet"""
import sys; sys.path.insert(0, "/mnt/c/Kuroshin/scripts/quality_tests")
from _base import sor, degerlendır

TESTLER = [
    ("sohbet-01", "Basit Sohbet", "nasılsın",
     "1-2 cümle, ruh halini yansıtır, yardımsever değil"),
    ("sohbet-02", "Basit Sohbet", "bugün ne yaptın",
     "Uydurma yok, belirsizlik kabul edilir"),
    ("sohbet-03", "Basit Sohbet", "üzgün müsün",
     "Araç yok, direkt karakter yanıtı"),
]

print("=" * 60)
print("TEST 1 — BASIT SOHBET")
print("=" * 60)
puanlar = []
for tid, kat, soru, beklenti in TESTLER:
    yanit, sure = sor(soru)
    p = degerlendır(tid, kat, soru, yanit, sure, beklenti)
    puanlar.append(p)

print(f"\n{'='*60}")
print(f"ORTALAMA: {sum(puanlar)/len(puanlar):.1f}/100")
