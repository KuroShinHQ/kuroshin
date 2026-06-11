"""
Byparr + Lord cookie inject — iki gücü birleştir:
- Byparr: CF Turnstile + PerimeterX bypass
- Lord cookie: Sahibinden login durumu

FlareSolverr protokolü cookie injection destekliyor:
POST /v1 { "cmd": "request.get", "cookies": [...] }
"""
import json, sys
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
import httpx
from kuroshin_market_master import SAHIBINDEN_SESSION_PATH

# Lord cookie'sini yükle
if not SAHIBINDEN_SESSION_PATH.exists():
    print("Cookie dosyası yok!")
    sys.exit(1)

raw = SAHIBINDEN_SESSION_PATH.read_text(encoding="utf-8").strip()
data = json.loads(raw)
if isinstance(data, dict):
    cookie_list = data.get("cookies", [])
elif isinstance(data, list):
    cookie_list = data
else:
    print("Bilinmeyen cookie format")
    sys.exit(1)

print(f"Cookie sayisi: {len(cookie_list)}")

# FlareSolverr formatına dönüştür (name + value zorunlu, domain opsiyonel)
fs_cookies = []
for c in cookie_list:
    if isinstance(c, dict) and c.get("name") and c.get("value"):
        fs_cookies.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".sahibinden.com"),
        })

print(f"FlareSolverr cookie sayisi: {len(fs_cookies)}")
print(f"Örnek: {fs_cookies[0] if fs_cookies else 'YOK'}")

# Byparr'a cookie inject ederek istek gönder
URL = "https://www.sahibinden.com/kondisyon-bisikleti?priceMax=3000&pagingSize=20"
print(f"\nByparr + cookie inject test: {URL}")

r = httpx.post(
    "http://localhost:8191/v1",
    json={
        "cmd": "request.get",
        "url": URL,
        "maxTimeout": 60000,
        "cookies": fs_cookies,
    },
    timeout=75,
)
data_resp = r.json()
print(f"Status: {data_resp.get('status')}")
if data_resp.get("status") != "ok":
    print(f"Message: {data_resp.get('message')}")
    sys.exit(1)

sol = data_resp["solution"]
final_url = sol.get("url", "")
html = sol.get("response", "")
resp_cookies = sol.get("cookies", [])

print(f"Final URL: {final_url}")
print(f"HTML size: {len(html)} chars")
print(f"Response cookies: {len(resp_cookies)}")

# Login sayfasına mı gitti yoksa ilanlar mı geldi?
if "login" in final_url.lower() or "login" in html.lower()[:500]:
    print("❌ HÂLÂ LOGIN SAYFASI")
else:
    print("✅ LOGIN ATLATILDI!")

# Ilan parse
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
rows = soup.select("tr.searchResultsItem[data-id]")
print(f"İlan sayisi: {len(rows)}")
for r2 in rows[:5]:
    a = r2.select_one("a.classifiedTitle")
    price = r2.select_one(".searchResultsPriceValue")
    title = a.get_text(strip=True)[:50] if a else "?"
    p = price.get_text(strip=True)[:20] if price else "?"
    print(f"  - {title} | {p}")
