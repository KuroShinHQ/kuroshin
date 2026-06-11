"""
4-site mobile API / JSON endpoint araştırması
ML YOK, Telegram YOK, Playwright YOK
"""
import re
import json
import sys
sys.path.insert(0, '/mnt/c/Kuroshin/scripts')

try:
    import curl_cffi.requests as req
except ImportError:
    import requests as req

HEADERS_MOBILE = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'tr-TR,tr;q=0.9',
}

HEADERS_DESKTOP = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'tr-TR,tr;q=0.9',
}

def test(name, url, headers=None, impersonate='chrome124'):
    try:
        r = req.get(url, headers=headers or HEADERS_DESKTOP,
                    impersonate=impersonate, timeout=20)
        ct = r.headers.get('content-type', '?')[:50]
        is_json = 'json' in ct.lower()
        text_preview = r.text[:500] if is_json else ''
        print(f'\n[{name}] {r.status_code} | {len(r.text):,}c | json={is_json}')
        print(f'  Content-Type: {ct}')
        if is_json:
            print(f'  JSON: {text_preview}')
        return r
    except Exception as e:
        print(f'\n[{name}] FAIL: {e}')
        return None

print('=' * 60)
print('TRENDYOL API ARAŞTIRMASI')
print('=' * 60)

# Trendyol — bilinen internal API endpoint'leri
r1 = test('TY web search HTML', 'https://www.trendyol.com/sr?q=kondisyon+bisikleti&pi=1')
if r1 and r1.status_code == 200:
    html = r1.text
    # __NEXT_DATA__ (Next.js SSR/ISR)
    nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if nd:
        try:
            data = json.loads(nd.group(1))
            print('  __NEXT_DATA__ BULUNDU — keys:', list(data.keys())[:5])
        except:
            print('  __NEXT_DATA__ var ama parse edilemedi')
    else:
        print('  __NEXT_DATA__: YOK (CSR)')

    # brandName JSON pattern
    brands = re.findall(r'"brandName"\s*:\s*"([^"]+)"', html)
    print(f'  brandName pattern: {len(brands)} — {brands[:5]}')

    # productName pattern
    names = re.findall(r'"name"\s*:\s*"([^"]{10,60})"', html)
    print(f'  name pattern (ilk 5): {names[:5]}')

    # Fiyat pattern
    prices = re.findall(r'"price"\s*:\s*(\d+\.?\d*)', html)
    print(f'  price pattern: {len(prices)} — {prices[:5]}')

# Trendyol mobile API denemesi
test('TY mobile API v1', 'https://api.trendyol.com/sapphire/api/v1/product/search?q=bisiklet&pi=1&culture=tr-TR', HEADERS_MOBILE)
test('TY mobile API v2', 'https://api.trendyol.com/discovery-web/api/v2/product/search?q=bisiklet', HEADERS_MOBILE)

print('\n' + '=' * 60)
print('HEPSİBURADA API ARAŞTIRMASI')
print('=' * 60)

r2 = test('HB web search HTML', 'https://www.hepsiburada.com/ara?q=kondisyon+bisikleti')
if r2 and r2.status_code == 200:
    html = r2.text
    # JSON-LD
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f'  JSON-LD blok sayısı: {len(ld)}')
    if ld:
        try:
            d = json.loads(ld[0])
            print(f'  JSON-LD[0] type: {d.get("@type","?")}')
        except:
            pass

    # HB data attribute
    items = re.findall(r'data-productid="([^"]+)"', html)
    print(f'  data-productid: {len(items)} ürün')

    names = re.findall(r'data-product-name="([^"]+)"', html)
    print(f'  data-product-name: {names[:3]}')

    prices = re.findall(r'"price"\s*:\s*"?(\d+[\.,]\d+)"?', html)
    print(f'  price pattern: {prices[:5]}')

# HB API denemeleri
test('HB search API v1', 'https://www.hepsiburada.com/api/search?q=kondisyon+bisikleti&start=0&rows=12')
test('HB search API v2', 'https://productgw.hepsiburada.com/api/search?q=kondisyon+bisikleti')

print('\n' + '=' * 60)
print('SAHİBİNDEN API ARAŞTIRMASI')
print('=' * 60)

r3 = test('SAH web search', 'https://www.sahibinden.com/arama?query=bisiklet&pagingSize=50')
if r3 and r3.status_code == 200:
    html = r3.text
    print(f'  Char: {len(html):,}')
    # login redirect kontrolü
    if 'giris' in html.lower() or 'login' in html.lower():
        print('  LOGIN REDIRECT: var')
    else:
        print('  LOGIN REDIRECT: yok')
    # ilan sayısı
    items = re.findall(r'class="searchResultsItem"', html)
    print(f'  searchResultsItem: {len(items)}')

# Sahibinden mobile API
test('SAH mobile API', 'https://api.sahibinden.com/api/search?query=bisiklet', HEADERS_MOBILE)
test('SAH classified', 'https://classified.sahibinden.com/api/v1/listings?q=bisiklet', HEADERS_MOBILE)

print('\n' + '=' * 60)
print('EPEY (zaten çalışıyor, kontrol)')
print('=' * 60)
r4 = test('EPEY kondisyon', 'https://www.epey.com/kondisyon-bisikleti/')
if r4 and r4.status_code == 200:
    html = r4.text
    links = re.findall(r'href="(/kondisyon-bisikleti/[^"]+\.html)"', html)
    print(f'  Ürün linki: {len(links)} — {links[:3]}')

print('\nTEST TAMAM')
