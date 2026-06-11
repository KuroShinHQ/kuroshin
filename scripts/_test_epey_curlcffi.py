"""
Epey curl_cffi parser testi — Playwright olmadan çalışıyor mu?
Kanıt: isim + fiyat çiftleri çıkıyor mu?
"""
import sys, re, time
sys.path.insert(0, '/mnt/c/Kuroshin/scripts')
try:
    import curl_cffi.requests as req
except ImportError:
    import requests as req
from bs4 import BeautifulSoup

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
    'Accept': 'text/html,*/*',
}

def parse_epey(html: str, budget: float = 99999, limit: int = 10) -> list:
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    price_links = soup.select('a[href*="#fiyatlar"]')

    for link in price_links:
        href = link.get('href', '')
        if '#fiyatlar' not in href:
            continue

        # Tam URL veya relative — normalize et
        full_url = href.split('#')[0]
        if not full_url or '.html' not in full_url:
            continue
        # URL her zaman https://www.epey.com ile başlıyor
        product_url = full_url if full_url.startswith('http') else f'https://www.epey.com{full_url}'

        # Fiyat: "6.229,10 TL 6 site, 6 fiyat"
        text = link.get_text(' ', strip=True)
        pm = re.search(r'([\d.]+),([\d]{2})\s*TL', text)
        if pm:
            try:
                price = float(pm.group(1).replace('.', '') + '.' + pm.group(2))
            except:
                price = 0.0
        else:
            pm2 = re.search(r'([\d.]+)\s*TL', text)
            price = float(pm2.group(1).replace('.', '')) if pm2 else 0.0

        if price <= 0 or price > budget:
            continue

        site_m = re.search(r'(\d+)\s*site', text)
        site_count = int(site_m.group(1)) if site_m else 0

        # İsim — aynı URL'li linkler içinde metin içereni bul
        name = ''
        for a in soup.find_all('a', href=lambda h: h and h.split('#')[0] == full_url):
            t = a.get_text(' ', strip=True)
            if t and len(t) > 3 and 'TL' not in t:
                name = t[:100]
                break
        # Yoksa title attribute'dan
        if not name:
            for a in soup.find_all('a', href=True):
                if a.get('href','').split('#')[0] == full_url and a.get('title'):
                    name = a.get('title','')[:100]
                    break
        # Yoksa slug'dan
        if not name:
            m = re.search(r'/([^/]+)\.html$', full_url)
            name = m.group(1).replace('-', ' ').title() if m else ''

        if not name:
            continue

        results.append({
            'name': name,
            'price': price,
            'url': product_url,
            'site_count': site_count,
        })

        if len(results) >= limit:
            break

    return results


# ── TEST ─────────────────────────────────────────────────────────────────────
print('Epey curl_cffi parser testi')
print('=' * 50)

t0 = time.time()
url = 'https://www.epey.com/kondisyon-bisikleti/'
r = req.get(url, impersonate='chrome131', timeout=20, headers=H)
elapsed = round(time.time() - t0, 2)
print(f'Fetch: {r.status_code} | {len(r.text):,}c | {elapsed}s')

products = parse_epey(r.text, budget=8000, limit=15)
print(f'Ürün sayısı: {len(products)}')
print()

for i, p in enumerate(products, 1):
    print(f'  {i}. {p["name"][:60]}')
    print(f'     {p["price"]:,.2f} TL | {p["site_count"]} site | {p["url"][:70]}')

if len(products) >= 5:
    prices = [p['price'] for p in products]
    print(f'\nFiyat aralığı: {min(prices):,.0f} — {max(prices):,.0f} TL')
    print('✅ Epey curl_cffi ÇALIŞIYOR — Playwright gerekmiyor!')
else:
    print('❌ Yeterli ürün yok')
