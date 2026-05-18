import asyncio
import httpx
from bs4 import BeautifulSoup
import re
import sys

# Force UTF-8 for clean output
sys.stdout.reconfigure(encoding="utf-8")

async def get_search_results(query):
    url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200: return None
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for row in soup.find_all("div", class_="result"):
        title_tag = row.find("a", class_="result__a")
        if title_tag:
            results.append({"title": title_tag.get_text(), "href": title_tag.get("href")})
    return results[:3]

async def run_scenarios():
    scenarios = [
        ("SIMPLE", "Current CEO of Microsoft"),
        ("MEDIUM", "NVIDIA RTX 5090 release date"),
        ("COMPLEX", "Model Context Protocol core concepts")
    ]
    print("🔱 --- KUROSHIN v1.9.0 LIVE PROOF --- 🔱\n")
    for name, query in scenarios:
        print(f"[{name}] QUERY: {query}")
        res = await get_search_results(query)
        if res:
            print(f"STATUS: SUCCESS - Found {len(res)} results")
            for i, r in enumerate(res, 1):
                print(f"  {i}. {r['title'][:70]}...")
        else:
            print("STATUS: FAILED (Blocked or No Results)")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(run_scenarios())
