import httpx
from bs4 import BeautifulSoup
import sys

def test_rss():
    print("--- [NUCLEAR RSS PROOF: BYPASSING EVERYTHING] ---")
    query = "NVIDIA Blackwell RTX 5090"
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url)
            print(f"HTTP DURUM: {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all('item')
            
            if items:
                print(f"ZAFER: {len(items)} HABER BULUNDU!")
                for item in items[:2]:
                    print(f"HABER: {item.title.get_text()}")
                return True
            else:
                print("HATA: RSS BOŞ DÖNDÜ!")
                return False
    except Exception as e:
        print(f"HATA: {e}")
        return False

if __name__ == "__main__":
    if not test_rss():
        sys.exit(1)
