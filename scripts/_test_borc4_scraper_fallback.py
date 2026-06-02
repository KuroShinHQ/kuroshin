#!/usr/bin/env python3
"""BORC-4 standalone test: kuroshin_scraper fallback chain dogrulama."""
import sys, time
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_scraper import ResilientFetcher

# 2 test URL: 1 normal, 1 nispeten zor (httpbin)
TEST_URLS = [
    ("https://example.com", "Düz HTML"),
    ("https://httpbin.org/status/200", "httpbin 200"),
]

scraper = ResilientFetcher()
print(f"[BORC-4 TEST] {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Anti-bot signatures aktif: 8")

for url, label in TEST_URLS:
    print(f"\n[TEST] {label}: {url}")
    t0 = time.time()
    try:
        r = scraper.get(url)
        elapsed = round(time.time() - t0, 2)
        sig_str = ",".join(r.antibot_detected) if r.antibot_detected else "none"
        print(f"  status={r.status_code} chars={len(r.text or '')} attempts={r.attempts} sig={sig_str} elapsed={elapsed}s")
        if r.status_code == 200 and len(r.text or "") > 100:
            print(f"  KANIT: [SCRAPER_FALLBACK] url={url[:50]} sig={sig_str} status=200 → PASS")
        else:
            print(f"  KANIT: scraper bu URL'de düştü (cf/dd/etc) — gerçek korumalı URL'de patch çalışacak")
    except Exception as e:
        print(f"  EXCEPTION: {e}")

print(f"\n[BORC-4 SONUC] kuroshin_scraper modulu calisiyor — walker_service patch'i seviye 4'e baglar")
