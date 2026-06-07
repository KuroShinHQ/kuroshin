#!/usr/bin/env python3
"""Lord'un Chrome cookie veritabanından Sahibinden cookies'i otomatik çıkar.
Lord doktrini: "C:\Magic'te coder yaptı, sen de yapabilir misin?"

Kullanım (PowerShell veya CMD):
    pip install browser-cookie3
    python C:\\Kuroshin\\scripts\\_export_sahibinden_cookies.py

Önkoşul:
- Chrome'da sahibinden.com'a login olmuş ol
- Chrome açık olabilir (modern browser-cookie3 lock issue yaşamaz)
"""
import sys
import json
from pathlib import Path

OUTPUT = Path("C:/Kuroshin/memory/sahibinden_session.json")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

try:
    import browser_cookie3
except ImportError:
    print("HATA: browser-cookie3 yüklü değil.")
    print("Kur: pip install browser-cookie3")
    sys.exit(1)


def extract_browser(name: str, getter):
    try:
        cj = getter(domain_name="sahibinden.com")
        cookies = []
        for c in cj:
            cookies.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain or ".sahibinden.com",
                "path": c.path or "/",
            })
        return cookies
    except Exception as e:
        print(f"  {name}: hata — {type(e).__name__}: {str(e)[:80]}")
        return []


print("Sahibinden cookies arıyorum 4 tarayıcıda...\n")
all_cookies = []
all_cookies += extract_browser("Chrome", browser_cookie3.chrome)
all_cookies += extract_browser("Edge", browser_cookie3.edge)
all_cookies += extract_browser("Firefox", browser_cookie3.firefox)
try:
    all_cookies += extract_browser("Brave", browser_cookie3.brave)
except AttributeError:
    pass

# Dedup name bazlı (aynı cookie iki browser'da varsa son okunan kalır)
seen = {}
for c in all_cookies:
    seen[c["name"]] = c
cookies_unique = list(seen.values())

if not cookies_unique:
    print("\nUYARI: Hiç sahibinden cookie bulunamadı.")
    print("Kontroller:")
    print("  - Chrome/Edge/Firefox'ta sahibinden.com'a login oldun mu?")
    print("  - Browser kapatıp tekrar deneyebilirsin (DB lock olabilir)")
    sys.exit(2)

OUTPUT.write_text(json.dumps(cookies_unique, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nOK: {len(cookies_unique)} cookie → {OUTPUT}")
print("Kuroshin sonraki market_master çağrısında otomatik kullanır.")
