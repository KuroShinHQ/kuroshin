import httpx
from bs4 import BeautifulSoup
import json
import sys

def test_raw_scrape():
    print("--- [RAW SCRAPE TEST: BYPASSING LIBRARIES] ---")
    query = "NVIDIA RTX 4060 latest driver"
    url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        with httpx.Client(follow_redirects=True, timeout=20.0) as client:
            resp = client.get(url, headers=headers)
            print(f"HTTP DURUM: {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all('div', class_='result')
            
            if results:
                print(f"ZAFER: {len(results)} SONUÇ BULUNDU!")
                for r in results[:2]:
                    title = r.find('a', class_='result__a').get_text().strip()
                    print(f"TITLE: {title}")
                return True
            else:
                print("HATA: HALA BLOKLANIYORUZ!")
                return False
    except Exception as e:
        print(f"KRİTİK HATA: {e}")
        return False

if __name__ == "__main__":
    if not test_raw_scrape():
        sys.exit(1)
