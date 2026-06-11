"""
Sahibinden mobile/API endpoint derin test.
api.sahibinden.com + gateway.sahibinden.com farklı IP → Cloudflare WAF değil.
"""
import re, subprocess, json
import curl_cffi.requests as req

def resolve_ip(host):
    try:
        out = subprocess.check_output(["nslookup", host, "8.8.8.8"], timeout=5, text=True, stderr=subprocess.DEVNULL)
        ips = [m for m in re.findall(r"Address:\s+([\d\.]+)", out) if m != "8.8.8.8"]
        return ips[-1] if ips else None
    except Exception:
        return None

def try_get(url, headers=None, note=""):
    try:
        r = req.get(url, headers=headers or {}, impersonate="chrome131", timeout=12, allow_redirects=True)
        ct = r.headers.get("content-type", "")
        snippet = r.text[:300] if len(r.text) > 0 else "(bos)"
        is_json = "json" in ct or snippet.strip().startswith("{") or snippet.strip().startswith("[")
        marker = "JSON✅" if is_json else "HTML"
        print(f"  {r.status_code} [{marker}] {url[:80]}")
        if note:
            print(f"    note: {note}")
        if is_json and r.status_code == 200:
            print(f"    JSON: {snippet[:400]}")
        elif r.status_code != 200:
            print(f"    snippet: {snippet[:150]}")
        return r
    except Exception as e:
        print(f"  ERR {url[:80]}: {str(e)[:60]}")
        return None

# --- api.sahibinden.com (ayrı IP: 172.64.154.73) ---
print("=== api.sahibinden.com ===")
api_ip = resolve_ip("api.sahibinden.com")
print(f"IP: {api_ip}")

API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Origin": "https://www.sahibinden.com",
    "Referer": "https://www.sahibinden.com/",
}

api_endpoints = [
    ("https://api.sahibinden.com/", "root"),
    ("https://api.sahibinden.com/v1/", "v1 root"),
    ("https://api.sahibinden.com/v2/", "v2 root"),
    ("https://api.sahibinden.com/search?q=bisiklet", "search v0"),
    ("https://api.sahibinden.com/v1/search?query=bisiklet&priceMax=3000", "v1 search"),
    ("https://api.sahibinden.com/v2/search?query=bisiklet&priceMax=3000", "v2 search"),
    ("https://api.sahibinden.com/classifieds/search?query=bisiklet", "classifieds search"),
    ("https://api.sahibinden.com/ads?q=bisiklet", "ads"),
]
for url, note in api_endpoints:
    try_get(url, headers=API_HEADERS, note=note)

# --- gateway.sahibinden.com ---
print("\n=== gateway.sahibinden.com ===")
gw_ip = resolve_ip("gateway.sahibinden.com")
print(f"IP: {gw_ip}")

gw_endpoints = [
    ("https://gateway.sahibinden.com/", "root"),
    ("https://gateway.sahibinden.com/search?query=bisiklet", "search"),
    ("https://gateway.sahibinden.com/classifieds?query=bisiklet", "classifieds"),
    ("https://gateway.sahibinden.com/api/search?q=bisiklet", "api search"),
]
for url, note in gw_endpoints:
    try_get(url, headers=API_HEADERS, note=note)

# --- Mobile User-Agent ile api.sahibinden.com ---
print("\n=== Mobile UA ile api.sahibinden.com ===")
MOBILE_UA = {
    "User-Agent": "sahibinden/6.8.0 (Android; Samsung Galaxy S21; Android 13)",
    "Accept": "application/json",
    "Accept-Language": "tr-TR",
    "X-App-Version": "6.8.0",
    "X-Platform": "android",
}
mobile_endpoints = [
    "https://api.sahibinden.com/search?q=bisiklet&priceMax=3000&category=bisiklet",
    "https://api.sahibinden.com/classifieds?q=bisiklet",
    "https://api.sahibinden.com/v1/classifieds/search?keyword=bisiklet&priceMax=3000",
]
for url in mobile_endpoints:
    try_get(url, headers=MOBILE_UA)
