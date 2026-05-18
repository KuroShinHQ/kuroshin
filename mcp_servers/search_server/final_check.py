# -*- coding: utf-8 -*-
import sys
from duckduckgo_search import DDGS

sys.stdout.reconfigure(encoding="utf-8")

def test():
    print("--- [GLOBAL TEST: DDGS v1.7.0] ---")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text("NVIDIA RTX 4060 latest driver", max_results=3))
        
        if results:
            for i, r in enumerate(results, 1):
                print(f"SEARCH_RESULT [{i}]:")
                print(f"TITLE: {r.get('title')}")
                print(f"URL: {r.get('href')}")
                print("---")
            print("\n🔱 TEST SUCCESSFUL: DDGS GLOBAL IS ACTIVE!")
        else:
            print("❌ HATA: Sonuç bulunamadı.")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test()
