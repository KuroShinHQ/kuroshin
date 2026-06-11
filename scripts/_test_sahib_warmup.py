"""
Sahibinden PerimeterX bypass — davranış warm-up testi
Strateji: anasayfa → gecikme → kategori → gecikme → arama
Residential IP (ev interneti) + curl_cffi chrome131 HTTP/2
"""
import time, random
import curl_cffi.requests as req
from bs4 import BeautifulSoup

SESSION = req.Session(impersonate="chrome131")

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def step(label, url, referer=None, delay=(2, 4)):
    if referer:
        HEADERS["Referer"] = referer
    elif "Referer" in HEADERS:
        del HEADERS["Referer"]
    wait = random.uniform(*delay)
    print(f"\n[{label}] {wait:.1f}s bekle → {url[:70]}")
    time.sleep(wait)
    r = SESSION.get(url, headers=HEADERS, timeout=20, allow_redirects=False)
    print(f"  HTTP {r.status_code}, {len(r.content)} bytes")
    if r.status_code in (301, 302):
        loc = r.headers.get("location", r.headers.get("Location", ""))
        print(f"  Redirect → {loc[:100]}")
    else:
        snippet = r.text[:400].replace("\n", " ")
        # PerimeterX veya CF var mı?
        if "perimeterx" in r.text.lower() or "_pxAppId" in r.text:
            print("  ⚠️  PerimeterX TESPİT EDİLDİ")
        elif "just a moment" in r.text.lower() or "cf-ray" in r.text.lower():
            print("  ⚠️  Cloudflare Turnstile TESPİT EDİLDİ")
        elif "olağandışı" in r.text.lower() or "olagandisi" in r.text.lower():
            print("  ⚠️  Bot tespiti (sahibinden kendi sistemi)")
        elif r.status_code == 200 and len(r.content) > 5000:
            print("  ✅ TEMİZ içerik")
            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("tr.searchResultsItem[data-id]")
            print(f"  İlan sayısı: {len(rows)}")
        print(f"  HTML: {snippet[:300]}")
    return r


# ADIM 1: Anasayfa (soğuk başlangıç)
r1 = step("ANASAYFA", "https://www.sahibinden.com/", delay=(1, 2))

# ADIM 2: checkLoading geç (eğer redirect ise)
if r1.status_code in (301, 302):
    loc = r1.headers.get("location", r1.headers.get("Location", ""))
    if "checkLoading" in loc:
        r1b = step("CHECK_LOADING", loc, referer="https://www.sahibinden.com/", delay=(3, 5))

# ADIM 3: Kategori sayfası
r2 = step("KATEGORİ", "https://www.sahibinden.com/bisiklet",
          referer="https://www.sahibinden.com/", delay=(3, 6))

# ADIM 4: Fiyat filtreli arama
r3 = step("ARAMA+FİYAT", "https://www.sahibinden.com/bisiklet?priceMax=3000&pagingSize=20",
          referer="https://www.sahibinden.com/bisiklet", delay=(2, 4))
