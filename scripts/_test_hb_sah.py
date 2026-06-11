"""
HB ve Sahibinden — static fetch derinlemesi
"""
import re, json, sys
sys.path.insert(0, '/mnt/c/Kuroshin/scripts')
try:
    import curl_cffi.requests as req
except ImportError:
    import requests as req
from bs4 import BeautifulSoup

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# ─── HEPSİBURADA ─────────────────────────────────────────────────────────────
print('=' * 60)
print('HEPSİBURADA — farklı URL denemesi')
print('=' * 60)

hb_urls = [
    ('HB search', 'https://www.hepsiburada.com/ara?q=kondisyon+bisikleti'),
    ('HB kategori', 'https://www.hepsiburada.com/spor-outdoor-aletleri-kondisyon-bisikletleri-c-3701'),
]

for name, url in hb_urls:
    r = req.get(url, impersonate='chrome124', timeout=20, headers=H)
    html = r.text
    print(f'\n[{name}] {r.status_code} | {len(html):,}c')

    soup = BeautifulSoup(html, 'html.parser')

    # Mevcut pattern
    cards1 = soup.select('li[class^="productListContent-"]')
    print(f'  li[class^=productListContent]: {len(cards1)}')

    # Alternatif: data-test-id
    cards2 = soup.select('[data-test-id*="product"]')
    print(f'  data-test-id*=product: {len(cards2)}')

    # JSON-LD
    ld_tags = soup.find_all('script', type='application/ld+json')
    print(f'  JSON-LD bloklar: {len(ld_tags)}')

    # window.__INITIAL_STATE__ veya __data
    scripts = soup.find_all('script')
    for s in scripts:
        t = s.get_text()
        if 'initialState' in t or '__data' in t or 'productList' in t:
            print(f'  ilginç script ({len(t)}c): {t[:200]}')
            break

    # Bracket-count JSON içinde ürün ara
    for key in ['"products":', '"productList":', '"listings":', '"items":']:
        pos = html.find(key)
        if pos > 0:
            print(f'  JSON key "{key}" pozisyon: {pos}')
            # İlk 200c
            print(f'  Çevre: {html[pos:pos+200]}')
            break

    # HB specific: __NEXT_DATA__
    nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if nd:
        try:
            d = json.loads(nd.group(1))
            print(f'  __NEXT_DATA__ BULUNDU! keys: {list(d.keys())}')
        except:
            print(f'  __NEXT_DATA__ var, parse edilemedi ({len(nd.group(1))}c)')

# ─── SAHİBİNDEN ──────────────────────────────────────────────────────────────
print('\n' + '=' * 60)
print('SAHİBİNDEN — cookie olmadan ne kadar geliyor?')
print('=' * 60)

sah_urls = [
    ('SAH kondisyon', 'https://www.sahibinden.com/kondisyon-bisikleti'),
    ('SAH arama', 'https://www.sahibinden.com/arama?query=kondisyon+bisikleti&pagingSize=50'),
    ('SAH API json', 'https://www.sahibinden.com/api/classifieds/search?query=kondisyon+bisikleti&pagingSize=20'),
]

for name, url in sah_urls:
    try:
        r = req.get(url, impersonate='chrome124', timeout=20, headers=H)
        html = r.text
        ct = r.headers.get('content-type', '?')[:40]
        print(f'\n[{name}] {r.status_code} | {len(html):,}c | {ct}')

        # Login redirect mi?
        if any(x in html.lower() for x in ['giris-yap', 'login', 'oturum']):
            print('  LOGIN REDIRECT: var')
        else:
            print('  Login yok!')

        # İlan var mı?
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('tr.searchResultsItem, .classified-ad-item, [class*="classified"]')
        print(f'  İlan elementi: {len(items)}')

        # JSON?
        if 'json' in ct.lower():
            print(f'  JSON: {html[:500]}')

        # title kontrolü
        title = soup.find('title')
        print(f'  Title: {title.get_text()[:80] if title else "yok"}')

    except Exception as e:
        print(f'[{name}] FAIL: {e}')
