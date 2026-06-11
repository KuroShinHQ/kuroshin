#!/usr/bin/env python3
"""
DEMO: Sahibinden.com — Ford Focus Fiyat Tarayıcısı
===================================================
Bu script, Sahibinden'de "Ford Focus" araması yapıp
ilanları fiyata göre sıralayarak ekrana ve CSV'ye yazar.

Çalıştırma:
  python demo_ford_focus.py                    # anonim (sınırlı erişim)
  python demo_ford_focus.py --cookies c.json   # kendi cookie dosyanızla
  python demo_ford_focus.py --max 30           # maksimum 30 ilan
  python demo_ford_focus.py --budget 300000    # bütçe filtresi (TL)
"""
import argparse
import sys
import time
from pathlib import Path

# scraper_paketi aynı dizinde mi diye kontrol et
sys.path.insert(0, str(Path(__file__).parent))

from scraper_paketi import PaketFetcher, parse_listings, export, print_table


SAHIBINDEN_FORD_FOCUS_URL = (
    "https://www.sahibinden.com/otomobil-ford-focus"
    "?pagingSize=50&sorting=price_asc"
)

SAHIBINDEN_ARAÇ_URL_TEMPLATE = (
    "https://www.sahibinden.com/otomobil-{marka}-{model}"
    "?pagingSize=50&sorting=price_asc"
)


def main():
    ap = argparse.ArgumentParser(description="Sahibinden Ford Focus Fiyat Tarayıcısı")
    ap.add_argument("--cookies", default="cookies.json",
                    help="Cookie dosyası yolu (varsayılan: cookies.json)")
    ap.add_argument("--max", type=int, default=20,
                    help="Maksimum ilan sayısı (varsayılan: 20)")
    ap.add_argument("--budget", type=float, default=0,
                    help="Maksimum bütçe TL (0 = sınırsız)")
    ap.add_argument("--output", default="ford_focus_ilanlari.csv",
                    help="Çıktı CSV dosyası (varsayılan: ford_focus_ilanlari.csv)")
    args = ap.parse_args()

    cookie_file = args.cookies if Path(args.cookies).exists() else None

    print("\n" + "="*60)
    print("  SAHIBINDEN FORD FOCUS FİYAT TARAYICI")
    print("="*60)
    if cookie_file:
        print(f"  Mod     : Cookie ile (yetkili erişim) ✓")
        print(f"  Cookie  : {cookie_file}")
    else:
        print(f"  Mod     : Anonim (cookie dosyası bulunamadı)")
        print(f"  Not     : Sahibinden 2026'da giriş gerektiriyor.")
        print(f"  Çözüm   : {args.cookies} dosyanızı ekleyin.")
    print(f"  URL     : {SAHIBINDEN_FORD_FOCUS_URL}")
    print(f"  Max     : {args.max} ilan")
    if args.budget > 0:
        print(f"  Bütçe   : {args.budget:,.0f} TL")
    print()

    fetcher = PaketFetcher(
        delay_min=3, delay_max=7,
        timeout=30, max_retries=3,
        cookie_file=cookie_file,
    )

    print("Sahibinden taranıyor...", end=" ", flush=True)
    t0 = time.time()
    result = fetcher.get(SAHIBINDEN_FORD_FOCUS_URL, mode="static")
    elapsed = round(time.time() - t0, 1)

    if result.blocked:
        print("ENGELLENDI")
        print(f"\n⚠️  Bot koruması aktif: {result.antibot or ['bilinmiyor']}")
        if not cookie_file:
            print("\nÇözüm adımları:")
            print("  1. Sahibinden.com'a tarayıcınızdan giriş yapın")
            print("  2. Tarayıcı eklentisiyle cookie'lerinizi JSON'a aktarın")
            print("     (EditThisCookie, Cookie-Editor vb.)")
            print(f"  3. {args.cookies} adıyla bu klasöre kaydedin")
            print("  4. Tekrar çalıştırın: python demo_ford_focus.py")
        sys.exit(1)

    if result.status_code != 200:
        print(f"HATA (HTTP {result.status_code})")
        sys.exit(1)

    print(f"OK ({elapsed}s, {len(result.html)//1024}KB)")

    # Parse
    listings = parse_listings(result.html, site_type="sahibinden",
                               site_label="Sahibinden")

    # Bütçe filtresi
    if args.budget > 0:
        before = len(listings)
        listings = [x for x in listings if x["price"] <= args.budget]
        print(f"Bütçe filtresi: {before} → {len(listings)} ilan ({args.budget:,.0f} TL)")

    if not listings:
        print("\nSonuç bulunamadı.")
        print("Öneri: URL'yi farklı bir arama ile deneyin veya cookie ekleyin.")
        sys.exit(0)

    # Fiyata göre sırala
    listings.sort(key=lambda x: x["price"])
    listings = listings[:args.max]

    # Konsol tablosu
    print()
    print_table(listings, sort_by="price", ascending=True)

    # İstatistik
    prices = [x["price"] for x in listings if x["price"] > 0]
    if prices:
        print(f"\n  En ucuz : {min(prices):,.0f} TL")
        print(f"  En pahalı: {max(prices):,.0f} TL")
        print(f"  Ortalama : {sum(prices)/len(prices):,.0f} TL")

    # CSV'ye kaydet
    out_path = export(listings, fmt="csv", path=args.output,
                      sort_by="price", ascending=True)
    print(f"\n✓ Sonuçlar kaydedildi: {out_path}")
    print("  Excel ile açmak için: dosyaya çift tıklayın")
    print("="*60)


if __name__ == "__main__":
    main()
