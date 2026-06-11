"""
Sahibinden JS bundle'larından API endpoint string'lerini çıkar.
Ana sayfa → JS URL'leri → her bundle'da /api/ pattern ara.
"""
import re, time
import curl_cffi.requests as req

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.sahibinden.com/",
}

# 1. Ana sayfa fetch (Byparr olmadan, sadece curl_cffi)
print("=== Ana sayfa ===")
r = req.get("https://www.sahibinden.com/", impersonate="chrome131", headers=HEADERS, timeout=15)
print(f"HTTP {r.status_code}, {len(r.content)} bytes")

# JS URL'leri bul
js_urls = re.findall(r'src=["\']?(https://static\.sahibinden\.com[^"\'>\s]+\.js[^"\'>\s]*)["\']?', r.text)
js_urls += re.findall(r'src=["\']?(/[^"\'>\s]+\.js(?:\?[^"\'>\s]*)?)["\']?', r.text)
print(f"JS URL sayisi: {len(js_urls)}")

# 2. Her JS bundle'ı fetch et, API endpoint ara
all_endpoints = set()
api_pattern = re.compile(r'["\`](/(?:api|classifieds|search|ads|ilan|listing)[^"\`\s<>]{3,80})["\`]')

s = req.Session(impersonate="chrome131")
checked = 0
for js_url in js_urls[:15]:  # ilk 15
    if not js_url.startswith("http"):
        js_url = "https://www.sahibinden.com" + js_url
    try:
        rj = s.get(js_url, timeout=10)
        if rj.status_code == 200 and len(rj.text) > 100:
            matches = api_pattern.findall(rj.text)
            new = set(matches) - all_endpoints
            if new:
                print(f"\n[{js_url[-60:]}] {len(new)} yeni endpoint:")
                for m in sorted(new)[:20]:
                    print(f"  {m}")
            all_endpoints |= set(matches)
            checked += 1
        time.sleep(0.5)
    except Exception as e:
        print(f"ERR {js_url[-50:]}: {str(e)[:40]}")

print(f"\nToplam benzersiz endpoint: {len(all_endpoints)} ({checked} bundle tarandı)")

# Öne çıkan olanları filtrele
interesting = [e for e in sorted(all_endpoints) if any(k in e for k in ["/api/", "/search", "/classify", "/ads", "/ilan", "/listing"])]
print(f"\nİlginç endpoint'ler ({len(interesting)}):")
for e in interesting[:30]:
    print(f"  {e}")
