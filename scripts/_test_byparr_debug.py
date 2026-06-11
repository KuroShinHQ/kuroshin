"""Byparr'dan gelen HTML'yi debug et - hangi selector'lar çalışıyor?"""
import httpx
from bs4 import BeautifulSoup

r = httpx.post(
    "http://localhost:8191/v1",
    json={"cmd": "request.get", "url": "https://www.sahibinden.com/kondisyon-bisikleti?priceMax=3000&pagingSize=20", "maxTimeout": 60000},
    timeout=70,
)
data = r.json()
sol = data["solution"]
html = sol["response"]
print("HTML size: {} chars".format(len(html)))
print("Status:", sol.get("status"))
print("URL:", sol.get("url"))

soup = BeautifulSoup(html, "html.parser")

# Çeşitli selector dene
selectors = [
    "tr.searchResultsItem",
    "tr[class*='searchResults']",
    "div[class*='searchResults']",
    "li[class*='searchResults']",
    "div[data-id]",
    "article",
    "[class*='classified']",
    "[class*='listing']",
    "td[class*='searchResultsTitle']",
]

for sel in selectors:
    found = soup.select(sel)
    if found:
        print("✅ '{}': {} eleman".format(sel, len(found)))
    else:
        print("❌ '{}': 0".format(sel))

# HTML başı
print("\n=HTML[0:500]==")
print(html[:500])

# Title
title = soup.find("title")
print("\nTitle:", title.text if title else "N/A")

# Bot sinyalleri
bot_keywords = ["turnstile", "perimeterx", "robot", "challenge", "captcha", "checkloading"]
for kw in bot_keywords:
    if kw in html.lower():
        print("⚠️ BOT SINYAL: '{}' bulundu".format(kw))
