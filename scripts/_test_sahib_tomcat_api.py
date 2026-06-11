"""
api.sahibinden.com Tomcat backend path keşfi.
Bilinen pattern'ler + classifiedEdr endpoint'leri dene.
"""
import re, json
import curl_cffi.requests as req

HEADERS_JSON = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Origin": "https://www.sahibinden.com",
    "Referer": "https://www.sahibinden.com/",
    "X-Requested-With": "XMLHttpRequest",
}

HEADERS_MOBILE = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json",
    "Accept-Language": "tr-TR",
    "X-App-Version": "6.8.0",
    "X-Platform": "android",
    "Authorization": "Bearer ",
}

def try_api(url, headers=None, label=""):
    try:
        r = req.get(url, headers=headers or HEADERS_JSON, impersonate="chrome131", timeout=10)
        ct = r.headers.get("content-type", "")
        is_json = "json" in ct or (r.text.strip()[:1] in ["{", "["])
        status = r.status_code
        snippet = r.text[:300]
        print(f"  {status} {'JSON✅' if is_json else 'HTML'} {url[-90:]}")
        if label:
            print(f"    [{label}]")
        if is_json and status in (200, 401, 403):
            print(f"    {snippet[:200]}")
        elif status == 200:
            print(f"    {snippet[:100]}")
    except Exception as e:
        print(f"  ERR {url[-80:]}: {str(e)[:50]}")

print("=== api.sahibinden.com — classifiedEdr pattern ===")
api_base = "https://api.sahibinden.com"
paths = [
    "/classifiedEdr/search?query=bisiklet&priceMax=3000",
    "/classifiedEdr/findMyREAEdr",
    "/classifiedEdr/list?query=bisiklet",
    "/classifiedEdr/classifieds?q=bisiklet",
    "/classifiedEdr/searchClassifieds?keyword=bisiklet",
    "/classified/search?query=bisiklet&priceMax=3000",
    "/classified/list?query=bisiklet",
    "/classifieds/search?keyword=bisiklet&priceMax=3000&currency=TRY",
    "/api/v2/collector",
    "/api/v2/search?q=bisiklet",
    "/api/v1/search?keyword=bisiklet",
    "/searchAds?query=bisiklet&priceMax=3000",
    "/search?query=bisiklet&priceMax=3000",
    "/listing/search?query=bisiklet",
    "/v2/classifieds?query=bisiklet",
    "/v3/classifieds/search?keyword=bisiklet",
]
for p in paths:
    try_api(api_base + p)

print("\n=== api.sahibinden.com — okhttp/Android UA ===")
android_paths = [
    "/classifieds/search?keyword=bisiklet&priceMax=3000",
    "/v1/classifieds?keyword=bisiklet&priceMax=3000",
    "/search?q=bisiklet&maxPrice=3000&lang=tr",
]
for p in android_paths:
    try_api(api_base + p, headers=HEADERS_MOBILE, label="android UA")

print("\n=== www.sahibinden.com — XHR endpoint'leri ===")
www_paths = [
    "https://www.sahibinden.com/searchAds?query=bisiklet&priceMax=3000",
    "https://www.sahibinden.com/searchResultsByKeyword?query=bisiklet",
    "https://www.sahibinden.com/searchAds/searchAdsJson?query=bisiklet",
    "https://www.sahibinden.com/api/v1/search?q=bisiklet&priceMax=3000",
    "https://www.sahibinden.com/classifiedDetail/getProductReviews",
]
for url in www_paths:
    try_api(url, headers=HEADERS_JSON)
