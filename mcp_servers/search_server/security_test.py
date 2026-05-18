import httpx
from bs4 import BeautifulSoup
import sys
import io

sys.stdout.reconfigure(encoding="utf-8")

def probe_fortress(level, name, url):
    print(f"\n--- [LEVEL {level}: {name}] ---")
    print(f"URL: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=15.0, headers=headers) as client:
            resp = client.get(url)
            print(f"HTTP STATUS: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text().strip()
                print(f"DURUM: ZAFER! {len(text)} karakter veri söküldü.")
                print(f"ÖNİZLEME: {text[:150].replace('\n', ' ')}...")
                return True
            else:
                print(f"DURUM: BOZGUN! Kalkanlara takıldık (HTTP {resp.status_code})")
                return False
    except Exception as e:
        print(f"DURUM: KRİTİK HATA! ({str(e)})")
        return False

if __name__ == "__main__":
    print("🔱 --- KUROSHIN SECURITY BREACH TEST --- 🔱")
    # L1: Wikipedia
    probe_fortress(1, "Wikipedia", "https://en.wikipedia.org/wiki/Artificial_intelligence")
    # L2: Reuters (Modern News Site)
    probe_fortress(2, "Reuters", "https://www.reuters.com/technology/")
    # L3: NVIDIA (High Security)
    probe_fortress(3, "NVIDIA", "https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/")
