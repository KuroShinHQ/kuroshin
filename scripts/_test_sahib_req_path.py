"""
robots.txt ipuçları: /req/ + /m/req/ + /api/ → test et
GitHub: sahibinden_api repoları incele
"""
import re
import curl_cffi.requests as req

s = req.Session(impersonate="chrome131")

HEADERS_XHR = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.sahibinden.com/bisiklet",
    "X-Requested-With": "XMLHttpRequest",
}

# 1. /req/ ve /m/req/ path testleri
print("=== /req/ path testleri ===")
req_paths = [
    "/req/classifiedSearch?query=bisiklet",
    "/req/classified/search?q=bisiklet",
    "/req/search?q=bisiklet&priceMax=3000",
    "/req/listing?category=bisiklet",
    "/req/classifiedList?q=bisiklet",
    "/m/req/classifiedSearch?q=bisiklet",
    "/m/req/search?q=bisiklet",
    "/m/req/listing?query=bisiklet&priceMax=3000",
]
for p in req_paths:
    url = "https://www.sahibinden.com" + p
    try:
        r = s.get(url, headers=HEADERS_XHR, timeout=10, allow_redirects=False)
        ct = r.headers.get("content-type","")
        is_json = "json" in ct or (r.text.strip()[:1] in ["{","["])
        loc = r.headers.get("location","") if r.status_code in (301,302,303,307,308) else ""
        print(f"  {r.status_code} {'JSON✅' if is_json else 'HTML'} {p}")
        if loc:
            print(f"    → {loc[:80]}")
        elif is_json and r.status_code in (200,400,401):
            print(f"    JSON: {r.text[:200]}")
    except Exception as e:
        print(f"  ERR {p}: {str(e)[:50]}")

# 2. GitHub repo'larına bak
print("\n=== GitHub sahibinden_api repo incele ===")
repos = [
    "https://raw.githubusercontent.com/ahmetcanalsat/sahibinden_api/main/README.md",
    "https://raw.githubusercontent.com/altnsysn/SAHIBINDEN_API/main/README.md",
    "https://raw.githubusercontent.com/ayseburhan/sahibindenWebApi/main/README.md",
    "https://api.github.com/repos/ahmetcanalsat/sahibinden_api/contents/",
    "https://api.github.com/repos/altnsysn/SAHIBINDEN_API/contents/",
]
for url in repos:
    try:
        r2 = s.get(url, timeout=10)
        print(f"\n  {r2.status_code} {url[-70:]}")
        if r2.status_code == 200:
            print(f"  {r2.text[:500]}")
    except Exception as e:
        print(f"  ERR: {e}")

# 3. robots.txt'den tam liste
print("\n=== robots.txt tam Disallow listesi ===")
try:
    r3 = s.get("https://www.sahibinden.com/robots.txt", timeout=10)
    disallow = re.findall(r'Disallow:\s+(\S+)', r3.text)
    print(f"{len(disallow)} Disallow kaydı:")
    for d in disallow:
        print(f"  {d}")
except Exception as e:
    print(f"ERR: {e}")
