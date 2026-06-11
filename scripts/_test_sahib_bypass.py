"""Sahibinden cookiesiz bypass testi — curl_cffi chrome131 (normal domain)"""
import curl_cffi.requests as req

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
}

# Test 1: Login olmadan arama — redirect=False, ne dönüyor?
print("=Test1: /bisiklet cookie YOK redirect=False==")
r = req.get(
    "https://www.sahibinden.com/bisiklet?priceMax=3000",
    headers=HEADERS,
    impersonate="chrome131",
    timeout=15,
    allow_redirects=False,
)
print(f"HTTP {r.status_code}, {len(r.content)} bytes")
loc = r.headers.get("location", r.headers.get("Location", "N/A"))
print(f"Location: {loc}")
print("HTML[:800]:", r.text[:800])

# Test 2: Redirect takip et
print("\n=Test2: redirect=True==")
r2 = req.get(
    "https://www.sahibinden.com/bisiklet?priceMax=3000",
    headers=HEADERS,
    impersonate="chrome131",
    timeout=15,
    allow_redirects=True,
)
print(f"HTTP {r2.status_code}, {len(r2.content)} bytes")
print("HTML[:800]:", r2.text[:800])

# Test 3: Arama API endpoint var mı?
print("\n=Test3: /arama?query=bisiklet==")
r3 = req.get(
    "https://www.sahibinden.com/arama?query=bisiklet&priceMax=3000",
    headers=HEADERS,
    impersonate="chrome131",
    timeout=15,
)
print(f"HTTP {r3.status_code}, {len(r3.content)} bytes")
print("HTML[:800]:", r3.text[:800])
