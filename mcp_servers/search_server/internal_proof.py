from duckduckgo_search import DDGS
import json
import sys

def run_nuclear_test():
    print("--- KUROSHIN NUCLEAR ENGINE: INTERNAL PROOF ---")
    query = "NVIDIA RTX 5090 launch date rumors"
    print(f"SORGULANAN: {query}")
    
    try:
        with DDGS() as ddgs:
            # Doğrudan kütüphane üzerinden veri çekme testi
            results = list(ddgs.text(query, max_results=3))
        
        if results:
            print("DURUM: BAŞARILI (VERİ ÇEKİLDİ)")
            print(json.dumps(results, indent=2))
            return True
        else:
            print("DURUM: BAŞARISIZ (SONUÇ BOŞ)")
            return False
    except Exception as e:
        print(f"DURUM: KRİTİK HATA! ({str(e)})")
        return False

if __name__ == "__main__":
    success = run_nuclear_test()
    if not success:
        sys.exit(1)
