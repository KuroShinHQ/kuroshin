# -*- coding: utf-8 -*-
import sys
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup

def test():
    print("--- [WSL BRIDGE: SEARCH TEST] ---")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text("Kuroshin AI latest news", max_results=2))
        
        if results:
            for i, r in enumerate(results, 1):
                print(f"SONUÇ {i}: {r.get('title')}")
                print(f"URL: {r.get('href')}")
            
            target = results[0].get('href')
            print(f"\n--- [WSL BRIDGE: SCRAPE TEST] ({target}) ---")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            with httpx.Client(follow_redirects=True, timeout=15.0) as client:
                resp = client.get(target, headers=headers)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text()[:300].replace("\n", " ")
                print(f"İÇERİK: {text}...")
                print("\n🔱 TEST BAŞARILI: WSL BRIDGE ÜZERİNDEN İNTERNETE ÇIKILDI!")
        else:
            print("❌ HATA: Sonuç bulunamadı.")
    except Exception as e:
        print(f"❌ KRİTİK HATA: {str(e)}")

if __name__ == "__main__":
    test()
