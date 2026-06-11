"""Byparr cookiesiz live kanıt — cookie dosyası geçici kaldırılır, gerçek Sahibinden araması yapılır."""
import sys, pathlib, time
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
import kuroshin_market_master as mm

orig = mm.SAHIBINDEN_SESSION_PATH
fake = pathlib.Path("/tmp/_sahib_bak.json")

import shutil
if orig.exists():
    shutil.copy2(str(orig), str(fake))
    orig.unlink()
    print("[TEST] Cookie dosyası geçici kaldırıldı")
else:
    print("[TEST] Cookie zaten yok")

try:
    listings = mm.fetch_sahibinden_byparr(
        "kondisyon bisikleti", budget=3000, log_fn=print
    )
    if listings:
        print("\n✅ BYPARR CANLI KANIT: {} ilan".format(len(listings)))
        for i, l in enumerate(listings[:5], 1):
            title = str(l.get("title", "?"))[:50]
            price = l.get("price", "?")
            print("  {}. {} | {}".format(i, title, price))
    else:
        print("❌ Byparr başarısız veya 0 ilan")
finally:
    if fake.exists():
        shutil.copy2(str(fake), str(orig))
        fake.unlink()
        print("[TEST] Cookie geri yüklendi")
