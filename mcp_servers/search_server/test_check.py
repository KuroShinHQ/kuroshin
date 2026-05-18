# -*- coding: utf-8 -*-
import sys
import io
from googlesearch import search
import httpx
from bs4 import BeautifulSoup
import re

# UTF-8 ZorlamasÄ±
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("--- [TEST 1: GOOGLE SEARCH] ---")
try:
    query = "NVIDIA RTX 4060 latest driver version 2026"
    results = list(search(query, num_results=3, lang="tr"))
    if results:
        for i, url in enumerate(results, 1):
            print(f"SONUÃ‡ {i}: {url}")
        
        target_url = results[0]
        print(f"\n--- [TEST 2: WALKER SCRAPER] ({target_url}) ---")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(target_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.extract()
            
            text = soup.get_text(separator="\n")
            text = re.sub(r"\n+", "\n", text)
            print(f"Ä°Ã‡ERÄ°K Ã–ZETÄ° (Ä°lk 500 Karakter):\n{text[:500]}")
            print("\nâ™¯ TEST BAÅžARILI: GOOGLE VE SCRAPER AKTÄ°F!")
    else:
        print("â Œ HATA: Google sonuÃ§ dÃ¶ndÃ¼rmedi.")
except Exception as e:
    print(f"â Œ KRÄ°TÄ°K HATA: {e}")
