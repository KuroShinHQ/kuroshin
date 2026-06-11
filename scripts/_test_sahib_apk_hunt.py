"""
Sahibinden mobile API endpoint keşfi:
1. APK meta bilgisinden URL ipucu (apkpure API)
2. GitHub public kod taraması
3. Wayback Machine (arşiv JS bundle analizi)
"""
import re
import curl_cffi.requests as req

s = req.Session(impersonate="chrome131")

# 1. apkpure — Sahibinden APK info (download URL + version)
print("=== APKPure Sahibinden info ===")
try:
    r = s.get(
        "https://apkpure.com/sahibinden-com/com.sahibinden.android/download",
        timeout=15
    )
    print(f"APKPure: HTTP {r.status_code}, {len(r.content)} bytes")
    # APK download URL bul
    apk_urls = re.findall(r'href=["\']([^"\']*\.apk[^"\']*)["\']', r.text)
    print(f"APK URL sayisi: {len(apk_urls)}")
    for u in apk_urls[:3]:
        print(f"  {u[:100]}")
except Exception as e:
    print(f"APKPure ERR: {e}")

# 2. GitHub code search — "sahibinden" + "api" endpoint'leri
print("\n=== GitHub public code — sahibinden API ===")
github_searches = [
    "https://api.github.com/search/code?q=sahibinden+classifiedEdr+language:java&sort=indexed&per_page=10",
    "https://api.github.com/search/code?q=api.sahibinden.com+language:java&sort=indexed&per_page=10",
    "https://api.github.com/search/repositories?q=sahibinden+api&sort=stars&per_page=10",
]
for url in github_searches:
    try:
        rg = s.get(url, headers={"Accept": "application/vnd.github.v3+json"}, timeout=10)
        import json
        data = json.loads(rg.text)
        if "items" in data:
            print(f"\n[{url[-60:]}] {data.get('total_count',0)} sonuç:")
            for item in data["items"][:5]:
                name = item.get("name") or item.get("full_name","?")
                html_url = item.get("html_url","")
                print(f"  {name}: {html_url}")
        else:
            print(f"ERR {url[-50:]}: {rg.text[:100]}")
    except Exception as e:
        print(f"GitHub ERR: {e}")

# 3. Wayback Machine — eski JS bundle'lardan endpoint bul
print("\n=== Wayback Machine — eski sahibinden JS ===")
try:
    wb = s.get(
        "http://timetravel.mementoweb.org/timemap/json/https://www.sahibinden.com/",
        timeout=15
    )
    print(f"Wayback: HTTP {wb.status_code}")
except Exception as e:
    print(f"Wayback ERR: {e}")

# 4. robots.txt + sitemap
print("\n=== robots.txt + sitemap ===")
for url in ["https://www.sahibinden.com/robots.txt", "https://www.sahibinden.com/sitemap.xml"]:
    try:
        r2 = s.get(url, timeout=10, allow_redirects=True)
        print(f"{r2.status_code} {url}")
        if r2.status_code == 200:
            # API path ipucu ara
            api_hints = re.findall(r'/api/[^\s<>]{3,60}', r2.text)
            if api_hints:
                print(f"  API hints: {api_hints[:10]}")
            else:
                print(f"  Content[:200]: {r2.text[:200]}")
    except Exception as e:
        print(f"ERR {url}: {e}")
