"""
Sahibinden /ajax endpoint'leri + GitHub reverse engineering repo analizi.
"""
import re, json
import curl_cffi.requests as req

s = req.Session(impersonate="chrome131")

HEADERS_XHR = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.sahibinden.com/bisiklet",
    "X-Requested-With": "XMLHttpRequest",
}

# 1. GitHub repo içerikleri — endpoint ipuçları
print("=== GitHub ahmetcanalsat/sahibinden_api içeriği ===")
try:
    r = s.get("https://api.github.com/repos/ahmetcanalsat/sahibinden_api/contents/", timeout=10)
    items = json.loads(r.text)
    for item in items:
        print(f"  {item['type']:6} {item['name']}")
    # Python/JS dosyalarını bul ve raw içeriğini çek
    for item in items:
        if item['name'].endswith(('.py','.js','.cs','.java','.ts','.md')):
            raw_url = item.get('download_url','')
            if raw_url:
                r2 = s.get(raw_url, timeout=10)
                if r2.status_code == 200:
                    # API URL pattern ara
                    urls = re.findall(r'https?://[^\s"\'<>]{10,100}', r2.text)
                    sahibinden_urls = [u for u in urls if 'sahibinden' in u.lower()]
                    if sahibinden_urls:
                        print(f"\n  [{item['name']}] Sahibinden URL'leri:")
                        for u in set(sahibinden_urls)[:10]:
                            print(f"    {u[:100]}")
except Exception as e:
    print(f"ERR: {e}")

print("\n=== GitHub altnsysn/SAHIBINDEN_API içeriği ===")
try:
    r3 = s.get("https://api.github.com/repos/altnsysn/SAHIBINDEN_API/contents/", timeout=10)
    items3 = json.loads(r3.text)
    for item in items3:
        print(f"  {item['type']:6} {item['name']}")
        if item['type'] == 'dir':
            r4 = s.get(item['url'], timeout=10)
            sub = json.loads(r4.text)
            for s_item in sub:
                if s_item['name'].endswith(('.cs','.py','.js','.json','.md')):
                    raw_url = s_item.get('download_url','')
                    if raw_url:
                        r5 = s.get(raw_url, timeout=10)
                        if r5.status_code == 200:
                            urls2 = re.findall(r'https?://[^\s"\'<>]{10,100}', r5.text)
                            sah = [u for u in urls2 if 'sahibinden' in u.lower()]
                            if sah:
                                print(f"\n    [{s_item['name']}] Sahibinden URL'leri:")
                                for u in set(sah)[:10]:
                                    print(f"      {u[:100]}")
except Exception as e:
    print(f"ERR: {e}")

# 2. /ajax endpoint'leri test et
print("\n\n=== /ajax endpoint testleri ===")
ajax_paths = [
    "/ajax/classifiedSearch?query=bisiklet&priceMax=3000",
    "/ajax/search?query=bisiklet",
    "/ajax/classifiedList?category=bisiklet&priceMax=3000",
    "/ajax/classifiedSearch/list?q=bisiklet",
    "/ajax/listing?q=bisiklet",
    "/ajax/getClassifieds?q=bisiklet&price_max=3000",
    "/ajax/searchAds?query=bisiklet",
    "/ajax/productSearch?keyword=bisiklet",
    "/ajax/classifiedSearch?searchText=bisiklet&priceMax=3000&pagingSize=20",
]

for p in ajax_paths:
    url = "https://www.sahibinden.com" + p
    try:
        r6 = s.get(url, headers=HEADERS_XHR, timeout=10, allow_redirects=False)
        ct = r6.headers.get("content-type","")
        is_json = "json" in ct or (r6.text.strip()[:1] in ["{","["])
        loc = r6.headers.get("location","") if r6.status_code in (301,302,303) else ""
        print(f"  {r6.status_code} {'JSON✅' if is_json else 'HTML'} {p}")
        if loc:
            print(f"    → {loc[:80]}")
        elif is_json and r6.status_code in (200,400,401,403):
            print(f"    JSON: {r6.text[:300]}")
        elif r6.status_code == 200:
            print(f"    {r6.text[:150]}")
    except Exception as e:
        print(f"  ERR {p}: {str(e)[:50]}")
