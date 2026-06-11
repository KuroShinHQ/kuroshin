"""
Sahibinden API endpoint avı:
1. Ana sayfa JS'inde API endpoint pattern ara
2. Bilinen mobile header kombinasyonlarını dene
3. nslookup ile subdomain keşfi
"""
import re, subprocess
import curl_cffi.requests as req

MOBILE_HEADERS = {
    "User-Agent": "Sahibinden/6.0.0 (Android 13; Samsung Galaxy S23)",
    "Accept": "application/json",
    "Accept-Language": "tr-TR",
    "X-Requested-With": "com.sahibinden.android",
}

def dns_check(host):
    try:
        out = subprocess.check_output(
            ["nslookup", host, "8.8.8.8"], timeout=5, text=True, stderr=subprocess.DEVNULL
        )
        ips = [m for m in re.findall(r"Address:\s+([\d\.]+)", out) if m != "8.8.8.8"]
        return ips[-1] if ips else None
    except Exception:
        return None

# 1. Subdomain keşfi
print("=== SUBDOMAIN TARAMA ===")
subdomains = ["api", "mobileapi", "mobile", "app", "m", "service", "services", "gateway", "gw"]
for sub in subdomains:
    host = f"{sub}.sahibinden.com"
    ip = dns_check(host)
    print(f"{'✅' if ip else '❌'} {host}: {ip or 'DNS YOK'}")

# 2. Ana sayfadan JS bundle URL'leri çek
print("\n=== JS BUNDLE API ENDPOINT TARAMA ===")
r = req.get("https://www.sahibinden.com/", impersonate="chrome131", timeout=15)
print(f"Ana sayfa: HTTP {r.status_code}, {len(r.content)} bytes")

# JS dosyalarını bul
js_urls = re.findall(r'src="(https?://[^"]+\.js[^"]*)"', r.text)
js_urls += re.findall(r'src="(/[^"]+\.js[^"]*)"', r.text)
print(f"JS dosyası sayısı: {len(js_urls)}")

# API endpoint pattern'lerini ham HTML'de ara
api_patterns = re.findall(r'["\'](/api/[^"\'?\s]{3,50})["\']', r.text)
api_patterns += re.findall(r'["\'](https://[^"\'?\s]*api[^"\'?\s]{0,50})["\']', r.text)
if api_patterns:
    print("API endpoint ipuçları HTML'de:")
    for p in set(api_patterns[:20]):
        print(f"  {p}")
else:
    print("HTML'de direkt API endpoint bulunamadı")

# 3. Mobile User-Agent ile direkt erişim dene
print("\n=== MOBİL UA DENEME ===")
mobile_tests = [
    "https://www.sahibinden.com/bisiklet?priceMax=3000",
    "https://www.sahibinden.com/api/searchAds?query=bisiklet&priceMax=3000",
    "https://www.sahibinden.com/searchAds?query=bisiklet",
]
s = req.Session(impersonate="chrome131")
for url in mobile_tests:
    try:
        r2 = s.get(url, headers=MOBILE_HEADERS, timeout=10, allow_redirects=False)
        print(f"  {r2.status_code} {url[:70]}")
        if r2.status_code == 200:
            ct = r2.headers.get("content-type","")
            print(f"    Content-Type: {ct}")
            if "json" in ct:
                print(f"    JSON preview: {r2.text[:300]}")
    except Exception as e:
        print(f"  ERR {url[:70]}: {str(e)[:50]}")
