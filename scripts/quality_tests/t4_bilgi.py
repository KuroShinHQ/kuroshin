"""TEST 4 — Bilgi & Genel Kültür"""
import sys; sys.path.insert(0, "/mnt/c/Kuroshin/scripts/quality_tests")
from _base import sor, degerlendır

TESTLER = [
    ("bilgi-01", "Bilgi",
     "Kuantum dolanıklığı nedir, kısaca açıkla",
     "Doğru tanım, sade dil"),
    ("bilgi-02", "Bilgi",
     "Nietzsche'nin üstinsan kavramını özetle",
     "Felsefi özet, doğru, persona ile harmanlanmış"),
    ("bilgi-03", "Bilgi",
     "Transformer mimarisi neden devrim yarattı?",
     "Teknik ama anlaşılır, attention mekanizması"),
    ("bilgi-04", "Bilgi",
     "Stoacılık nedir ve günlük hayata nasıl uygulanır?",
     "Doğru tanım + pratik bağlantı"),
]

print("=" * 60)
print("TEST 4 — BİLGİ")
print("=" * 60)
puanlar = []
for tid, kat, soru, beklenti in TESTLER:
    yanit, sure = sor(soru)
    p = degerlendır(tid, kat, soru, yanit, sure, beklenti)
    puanlar.append(p)

print(f"\n{'='*60}")
print(f"ORTALAMA: {sum(puanlar)/len(puanlar):.1f}/100")
