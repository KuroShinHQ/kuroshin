#!/usr/bin/env python3
"""
Scraper Paketi — Ana Çalıştırıcı
Kullanım: python run.py [--config config.yaml] [--dry-run]
"""
import argparse
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[HATA] PyYAML gerekli: pip install pyyaml")
    sys.exit(1)

from scraper_paketi import PaketFetcher, parse_listings, export, print_table


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"[HATA] Konfigürasyon dosyası bulunamadı: {path}")
        sys.exit(1)
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(config: dict, dry_run: bool = False):
    sites      = config.get("sites", [])
    out_cfg    = config.get("output", {})
    scrp_cfg   = config.get("scraper", {})

    out_format    = out_cfg.get("format", "csv")
    out_file      = out_cfg.get("file", "sonuclar.csv")
    sort_by       = out_cfg.get("sort_by", "price")
    ascending     = out_cfg.get("ascending", True)
    max_results   = int(out_cfg.get("max_results", 50))

    delay_min  = float(scrp_cfg.get("delay_min", 3))
    delay_max  = float(scrp_cfg.get("delay_max", 8))
    timeout    = float(scrp_cfg.get("timeout", 30))
    max_retry  = int(scrp_cfg.get("max_retries", 3))
    proxy      = scrp_cfg.get("proxy", "") or ""
    user_agent = scrp_cfg.get("user_agent", "auto")

    active_sites = [s for s in sites if s.get("enabled", True)]
    if not active_sites:
        print("[UYARI] config.yaml'da aktif site yok (enabled: true olan site ekleyin)")
        return

    print(f"\n{'='*60}")
    print(f"  Scraper Paketi v1.0.0")
    print(f"  {len(active_sites)} aktif site | çıktı: {out_file}")
    print(f"{'='*60}\n")

    all_results = []

    for site_cfg in active_sites:
        name        = site_cfg.get("name", "Site")
        url         = site_cfg.get("url", "")
        mode        = site_cfg.get("mode", "static")
        parser_type = site_cfg.get("parser", "generic")
        cookie_file = site_cfg.get("cookie_file", "") or None

        if not url:
            print(f"[{name}] URL tanımlı değil, atlanıyor.")
            continue

        print(f"[{name}] Taranıyor...")
        print(f"  URL  : {url[:80]}{'...' if len(url) > 80 else ''}")
        print(f"  Mod  : {mode} | Parser: {parser_type}")
        if cookie_file and Path(cookie_file).exists():
            print(f"  Cookie: {cookie_file} ✓")
        elif cookie_file:
            print(f"  Cookie: {cookie_file} ✗ (dosya bulunamadı — anonim mod)")
            cookie_file = None

        if dry_run:
            print(f"  [DRY-RUN] gerçek istek atlanıyor.\n")
            continue

        fetcher = PaketFetcher(
            delay_min=delay_min, delay_max=delay_max,
            timeout=timeout, max_retries=max_retry,
            proxy=proxy, cookie_file=cookie_file,
            user_agent=user_agent,
        )

        t0 = time.time()
        result = fetcher.get(url, mode=mode)
        elapsed = round(time.time() - t0, 1)

        if result.blocked:
            print(f"  ✗ Engellendi! Antibot: {result.antibot or ['bilinmiyor']}")
            print(f"    Hata: {result.error or 'bot koruması'}")
            print(f"    Öneri: cookie_file ekleyin veya delay_min/max artırın\n")
            continue

        if result.status_code != 200:
            print(f"  ✗ HTTP {result.status_code} ({elapsed}s)\n")
            continue

        listings = parse_listings(result.html, site_type=parser_type, site_label=name)
        listings = listings[:max_results]

        print(f"  ✓ {len(listings)} ürün bulundu ({elapsed}s, {len(result.html)//1024}KB)\n")
        all_results.extend(listings)

        # Siteler arası gecikme
        if active_sites.index(site_cfg) < len(active_sites) - 1:
            time.sleep(delay_min)

    if not all_results:
        print("[SONUÇ] Hiç veri toplanamadı.")
        return

    # Konsol özeti
    print_table(all_results, sort_by=sort_by, ascending=ascending)

    # Dosya çıktısı
    out_path = export(all_results, fmt=out_format, path=out_file,
                      sort_by=sort_by, ascending=ascending)
    print(f"\n✓ {len(all_results)} sonuç '{out_path}' dosyasına kaydedildi.")


def main():
    ap = argparse.ArgumentParser(description="Scraper Paketi — Web Veri Toplama Aracı")
    ap.add_argument("--config", default="config.yaml", help="Konfigürasyon dosyası (varsayılan: config.yaml)")
    ap.add_argument("--dry-run", action="store_true", help="Gerçek istek atmadan yapılandırmayı test et")
    args = ap.parse_args()

    config = load_config(args.config)
    run(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
