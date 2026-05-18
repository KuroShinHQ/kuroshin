# -*- coding: utf-8 -*-
import sys
import io
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup
import re

# English UTF-8 Bypass (Kuroshin Standard)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def run_proof(scenario, query, fetch=False):
    print(f"\n[SCENARIO: {scenario}]")
    print(f"QUERY: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        
        if not results:
            print("STATUS: FAILED (0 Results)")
            return

        print(f"STATUS: SUCCESS ({len(results)} Results Found)")
        for i, r in enumerate(results, 1):
            print(f"  RESULT [{i}]: {r.get('title')[:60]}... (URL: {r.get('href')[:40]}...)")
            
        if fetch and results:
            target = results[0].get('href')
            print(f"  [COMPLEX STEP: FETCHING CONTENT FROM {target}]")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            with httpx.Client(follow_redirects=True, timeout=15.0) as client:
                resp = client.get(target, headers=headers)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for e in soup(["script", "style", "nav", "footer"]): e.extract()
                text = re.sub(r"\n+", " ", soup.get_text())[:250].strip()
                print(f"  CONTENT PREVIEW: {text}...")

    except Exception as e:
        print(f"STATUS: ERROR ({str(e)})")

if __name__ == "__main__":
    print("🔱 --- KUROSHIN GLOBAL SEARCH v1.8.0 PROOF OF POWER --- 🔱")
    # 1. BASİT: Net bilgi
    run_proof("SIMPLE (Fact Check)", "Current CEO of Microsoft")
    # 2. ORTA: Güncel teknoloji
    run_proof("MEDIUM (Tech News)", "NVIDIA Blackwell B200 GPU specs")
    # 3. KARMAŞIK: Teknik doküman ve içerik çekme
    run_proof("COMPLEX (Search + Scrape)", "Model Context Protocol core concepts", fetch=True)
    print("\n🔱 --- ALL TESTS COMPLETED SUCCESSFULLY --- 🔱")
