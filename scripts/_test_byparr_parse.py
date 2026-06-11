"""Byparr → Sahibinden parse testi"""
import httpx
from bs4 import BeautifulSoup

r = httpx.post(
    "http://localhost:8191/v1",
    json={"cmd": "request.get", "url": "https://www.sahibinden.com/bisiklet?priceMax=3000", "maxTimeout": 60000},
    timeout=70,
)
sol = r.json()["solution"]
body = sol["response"]
cookies = sol["cookies"]

soup = BeautifulSoup(body, "html.parser")
rows = soup.select("tr.searchResultsItem[data-id]")
print(f"İlan sayısı: {len(rows)}")
for row in rows[:8]:
    title = row.select_one("a.classifiedTitle")
    price = row.select_one(".searchResultsPriceValue")
    t = title.text.strip()[:60] if title else "?"
    p = price.text.strip() if price else "?"
    print(f"  - {t} | {p}")

print(f"\nCookies ({len(cookies)}): {[c['name'] for c in cookies[:6]]}")
