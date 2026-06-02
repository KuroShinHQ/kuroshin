#!/usr/bin/env python3
"""DALGA-6 prob: 4 sitede scraper direkt test (walker bypass). Cloudflare/anti-bot durum keşfi."""
import sys, time, re
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_scraper import ResilientFetcher

SITES = [
    ("Sahibinden",    "https://www.sahibinden.com/kondisyon-bisikleti"),
    ("Trendyol",      "https://www.trendyol.com/sr?wc=104027"),  # Kondisyon Bisikleti kategori
    ("Hepsiburada",   "https://www.hepsiburada.com/kondisyon-bisikletleri-c-60003109"),
    ("Epey",          "https://www.epey.com/kondisyon-bisikleti/"),
]

CF_SIGS = ["just a moment", "cf-ray", "cf_chl_", "cloudflare", "datadome", "checking your browser", "_cf_bm"]

print(f"[DALGA-6 4SITE PROB] {time.strftime('%H:%M:%S')}")
print(f"  Anti-bot detect: 8 sig (kuroshin_scraper)")
print()

scraper = ResilientFetcher(timeout=30.0, max_retries=2)

for name, url in SITES:
    print(f"=== {name}: {url}")
    t0 = time.time()
    try:
        r = scraper.get(url)
        elapsed = round(time.time() - t0, 1)
        text_len = len(r.text or "")
        cf_hit = []
        for sig in CF_SIGS:
            if r.text and sig.lower() in r.text.lower():
                cf_hit.append(sig)
        sig_str = ",".join(r.antibot_detected) if r.antibot_detected else "none"
        cf_str = ",".join(cf_hit[:3]) if cf_hit else "none"
        verdict = "PASS" if (r.status_code == 200 and text_len > 5000 and not cf_hit) else \
                  "PARTIAL" if (r.status_code == 200 and text_len > 500) else \
                  "BLOCKED"
        print(f"  status={r.status_code} chars={text_len} attempts={r.attempts} elapsed={elapsed}s")
        print(f"  scraper_sig={sig_str}  cf_text_sig={cf_str}")
        print(f"  VERDICT: {verdict}")
        # Title ipucu
        if r.text and "<title" in r.text.lower():
            tm = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.IGNORECASE | re.DOTALL)
            if tm:
                print(f"  title: {tm.group(1).strip()[:80]}")
        print()
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {str(e)[:100]}")
        print()

print(f"[DALGA-6 PROB SONUC] {time.strftime('%H:%M:%S')}")
