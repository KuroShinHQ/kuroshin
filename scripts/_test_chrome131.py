"""
chrome124 vs chrome131 karşılaştırma — HB Akamai bypass
Kanıt: hangi version daha fazla/kaliteli ürün çekiyor?
"""
import sys, time, re
sys.path.insert(0, '/mnt/c/Kuroshin/scripts')
try:
    import curl_cffi.requests as req
except ImportError:
    import requests as req
from bs4 import BeautifulSoup

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
}

def test_hb(impersonate, label):
    url = 'https://www.hepsiburada.com/ara?q=kondisyon+bisikleti'
    t0 = time.time()
    r = req.get(url, impersonate=impersonate, timeout=20, headers=H)
    elapsed = round(time.time() - t0, 2)
    soup = BeautifulSoup(r.text, 'html.parser')
    cards = soup.select('li[class^="productListContent-"]')

    # İsim çek
    names = []
    prices = []
    for card in cards[:5]:
        # İsim — farklı seçiciler dene
        name = ''
        for sel in ['h3', 'h2', '[class*="ProductName"]', 'a[title]', 'span[class*="name"]', 'span[class*="Name"]']:
            el = card.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(strip=True)[:60]
                break
        if not name:
            a = card.find('a', href=True)
            name = a.get('title', '')[:60] if a else ''

        # Fiyat
        price = ''
        for sel in ['[class*="price"][class*="current"]', '[class*="Price"]', '[data-test-id*="price"]',
                    'span[class*="finalPrice"]', 'div[class*="price"]']:
            el = card.select_one(sel)
            if el and el.get_text(strip=True):
                price = el.get_text(strip=True)[:30]
                break

        if name:
            names.append(name)
        if price:
            prices.append(price)

    # data-* attribute'lar var mı?
    sample_attrs = dict(cards[0].attrs) if cards else {}
    data_keys = [k for k in sample_attrs if k.startswith('data-')]

    print(f'\n[{label}] status={r.status_code} | {len(r.text):,}c | {elapsed}s')
    print(f'  Kart sayısı: {len(cards)}')
    print(f'  İsimler: {names[:3]}')
    print(f'  Fiyatlar: {prices[:3]}')
    print(f'  data-* attrs: {data_keys[:5]}')
    return len(cards), names

print('HB Akamai bypass — chrome124 vs chrome131')
print('=' * 50)
n124, names124 = test_hb('chrome124', 'chrome124')
n131, names131 = test_hb('chrome131', 'chrome131')

print(f'\n--- SONUÇ ---')
print(f'chrome124: {n124} kart | chrome131: {n131} kart')
if n131 >= n124:
    print('✅ chrome131 kazandı veya eşit — geçiş ONAYLANDI')
else:
    print('⚠️ chrome124 daha iyi — geçiş gerekli değil')
