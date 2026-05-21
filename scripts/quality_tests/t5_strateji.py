"""TEST 5 — Stratejik & Analitik"""
import sys; sys.path.insert(0, "/mnt/c/Kuroshin/scripts/quality_tests")
from _base import sor, degerlendır

TESTLER = [
    ("strateji-01", "Stratejik",
     "Bir yapay zeka şirketi kurmak istiyorum. İlk 3 adımım ne olmalı?",
     "Somut adımlar, danışman değil analist, Kuroshin tonu"),
    ("strateji-02", "Stratejik",
     "En büyük teknoloji risklerini önceliklendir ve neden önemli olduklarını açıkla",
     "Önceliklendirilmiş, gerekçeli"),
    ("strateji-03", "Stratejik",
     "Rekabette üstünlük sağlamak için en kritik stratejik faktörler nelerdir?",
     "Keskin, somut, Kuroshin karakteriyle — stratejist bakışı"),
]

print("=" * 60)
print("TEST 5 — STRATEJİK")
print("=" * 60)
puanlar = []
for tid, kat, soru, beklenti in TESTLER:
    yanit, sure = sor(soru)
    p = degerlendır(tid, kat, soru, yanit, sure, beklenti)
    puanlar.append(p)

print(f"\n{'='*60}")
print(f"ORTALAMA: {sum(puanlar)/len(puanlar):.1f}/100")
