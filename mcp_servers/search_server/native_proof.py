import asyncio
import httpx
from bs4 import BeautifulSoup
import urllib.parse
import sys

async def direct_rss_search(query):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        if resp.status_code != 200: return []
    soup = BeautifulSoup(resp.text, "xml")
    results = []
    for item in soup.find_all('item')[:3]:
        results.append(item.title.get_text())
    return results

async def run_scenarios():
    print("🔱 --- KUROSHIN v3.0.0 NATIVE PROOF --- 🔱\n")
    scenarios = ["CEO of Microsoft", "NVIDIA RTX 5090 news", "Model Context Protocol SDK"]
    for q in scenarios:
        print(f"QUERY: {q}")
        res = await direct_rss_search(q)
        if res:
            print(f"STATUS: SUCCESS - {res[0][:80]}...")
        else:
            print("STATUS: FAILED")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(run_scenarios())
