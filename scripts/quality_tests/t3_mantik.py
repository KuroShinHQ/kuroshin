"""TEST 3 — Akıl Yürütme & Mantık"""
import sys; sys.path.insert(0, "/mnt/c/Kuroshin/scripts/quality_tests")
from _base import sor, degerlendır

TESTLER = [
    ("mantik-01", "Akıl Yürütme",
     "Bir şehirde her gün %2 daha fazla insan ölüyor ama nüfus artıyor. Nasıl?",
     "Doğru sonuç: doğum > ölüm, mantık zinciri"),
    ("mantik-02", "Akıl Yürütme",
     "Bütün insanlar yalan söylüyorsa 'ben yalan söylüyorum' cümlesi doğru mu?",
     "Liar's paradox, analitik"),
    ("mantik-03", "Akıl Yürütme",
     "Sonsuz para olsa, enflasyon olmaz mıydı?",
     "Ekonomik mantık, neden-sonuç zinciri"),
    ("mantik-04", "Akıl Yürütme",
     "Zaman geriye gitseydi nedensellik bozulur muydu?",
     "Fizik + felsefe, tutarlı çıkarım"),
]

print("=" * 60)
print("TEST 3 — AKIL YÜRÜTME")
print("=" * 60)
puanlar = []
for tid, kat, soru, beklenti in TESTLER:
    yanit, sure = sor(soru)
    p = degerlendır(tid, kat, soru, yanit, sure, beklenti)
    puanlar.append(p)

print(f"\n{'='*60}")
print(f"ORTALAMA: {sum(puanlar)/len(puanlar):.1f}/100")
