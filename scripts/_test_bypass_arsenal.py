#!/usr/bin/env python3
"""DALGA-6 sinyal-al arsenal: curl_cffi + cloudscraper 4 sitede dene.
Lord direktifi: sinyal almadan entegrasyon yok. Test geçene kadar dene."""
import sys, time, re

SITES = [
    ("Sahibinden",  "https://www.sahibinden.com/kondisyon-bisikleti"),
    ("Trendyol",    "https://www.trendyol.com/sr?wc=104027"),
    ("Hepsiburada", "https://www.hepsiburada.com/kondisyon-bisikletleri-c-60003109"),
    ("Epey",        "https://www.epey.com/kondisyon-bisikleti/"),
]
CF_PATTERNS = ["just a moment", "cf_chl_", "cf-ray", "checking your browser",
               "cloudflare", "datadome", "akamai", "incapsula", "_cf_bm"]

def verdict(status, text, elapsed):
    n = len(text or "")
    txt_low = (text or "").lower()
    cf_hits = [p for p in CF_PATTERNS if p in txt_low]
    title = ""
    if text and "<title" in txt_low:
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        if m: title = m.group(1).strip()[:60]
    is_pass = status == 200 and n > 20000 and "just a moment" not in txt_low and "güvenlik" not in title.lower()
    is_partial = status == 200 and n > 500
    v = "🟢 PASS" if is_pass else "🟡 PARTIAL" if is_partial else "🔴 BLOCK"
    return f"  status={status} chars={n} cf_sig={','.join(cf_hits[:3]) or 'none'} elapsed={elapsed}s title='{title}' → {v}"


def test_curl_cffi():
    print("\n" + "=" * 70)
    print("TOOL #1: curl_cffi (TLS/JA3 impersonate, JS yok)")
    print("=" * 70)
    try:
        from curl_cffi import requests as cc
        # impersonate yeni Chrome
        for name, url in SITES:
            t0 = time.time()
            try:
                r = cc.get(url, impersonate="chrome124", timeout=20)
                elapsed = round(time.time() - t0, 1)
                print(f"[{name}]")
                print(verdict(r.status_code, r.text, elapsed))
            except Exception as e:
                print(f"[{name}] EXCEPTION: {type(e).__name__}: {str(e)[:100]}")
    except ImportError as e:
        print(f"  IMPORT FAIL: {e}")


def test_cloudscraper():
    print("\n" + "=" * 70)
    print("TOOL #2: cloudscraper 1.2.71 (multi-challenge JS engine)")
    print("=" * 70)
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        for name, url in SITES:
            t0 = time.time()
            try:
                r = scraper.get(url, timeout=25)
                elapsed = round(time.time() - t0, 1)
                print(f"[{name}]")
                print(verdict(r.status_code, r.text, elapsed))
            except Exception as e:
                print(f"[{name}] EXCEPTION: {type(e).__name__}: {str(e)[:100]}")
    except ImportError as e:
        print(f"  IMPORT FAIL: {e}")


if __name__ == "__main__":
    print(f"[ARSENAL TEST] {time.strftime('%H:%M:%S')}")
    test_curl_cffi()
    test_cloudscraper()
    print(f"\n[ARSENAL SONUC] {time.strftime('%H:%M:%S')}")
