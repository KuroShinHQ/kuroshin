"""
Epey JSON araştırması + HB JSON script analizi
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
}

def bracket_extract(html, key):
    pos = html.find(key)
    if pos < 0: return None
    start = html.find('[', pos)
    if start < 0:
        start = html.find('{', pos)
    if start < 0: return None
    depth = 0
    in_str = False
    esc = False
    for j in range(start, min(start + 2000000, len(html))):
        c = html[j]
        if esc: esc = False; continue
        if c == '\\' and in_str: esc = True; continue
        if c == '"': in_str = not in_str; continue
        if in_str: continue
        if c in '[{': depth += 1
        elif c in ']}':
            depth -= 1
            if depth == 0:
                return html[start:j+1]
    return None

# ─── EPEY ────────────────────────────────────────────────────────────────────
print('=' * 60)
print('EPEY — JSON araştırması')
print('=' * 60)

r = req.get('https://www.epey.com/kondisyon-bisikleti/', impersonate='chrome124', timeout=20, headers=H)
html = r.text
print(f'HTML: {len(html):,}c | status: {r.status_code}')

soup = BeautifulSoup(html, 'html.parser')
title = soup.find('title')
print(f'Title: {title.get_text()[:80] if title else "yok"}')

# Fiyat linkleri (#fiyatlar) — mevcut yöntem
price_links = soup.select('a[href*="#fiyatlar"]')
print(f'#fiyatlar linkleri: {len(price_links)}')
for lnk in price_links[:3]:
    print(f'  {lnk.get("href", "")[:80]} | {lnk.get_text()[:40]}')

# JSON gömülü mü?
for key in ['"products":', '"items":', '"urunler":', '"listings":', '"data":']:
    raw = bracket_extract(html, key)
    if raw and len(raw) > 100:
        print(f'\nJSON key "{key}" BULUNDU ({len(raw)}c)')
        try:
            d = json.loads(raw)
            print(f'  Parse OK: {type(d).__name__} len={len(d) if isinstance(d, list) else list(d.keys())[:3]}')
            if isinstance(d, list) and d:
                print(f'  İlk item keys: {list(d[0].keys())[:8]}')
        except Exception as e:
            print(f'  Parse FAIL: {e}')
        break

# __NEXT_DATA__
nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if nd:
    print(f'\n__NEXT_DATA__ BULUNDU ({len(nd.group(1))}c)')

# ─── HB JSON SCRIPT ──────────────────────────────────────────────────────────
print('\n' + '=' * 60)
print('HEPSİBURADA — Script JSON içi ürün tara')
print('=' * 60)

r2 = req.get('https://www.hepsiburada.com/ara?q=kondisyon+bisikleti', impersonate='chrome124', timeout=20, headers=H)
html2 = r2.text
print(f'HTML: {len(html2):,}c')

# productState içinde ürünler var mı?
ps_raw = bracket_extract(html2, '"productState":')
if ps_raw:
    print(f'productState: {len(ps_raw):,}c')
    try:
        ps = json.loads(ps_raw)
        print(f'  keys: {list(ps.keys())[:10]}')
        # listings veya products
        for sub in ['listings', 'products', 'items', 'searchResult']:
            if sub in ps:
                items = ps[sub]
                print(f'  ps["{sub}"]: {type(items).__name__} len={len(items) if isinstance(items, (list,dict)) else "?"}')
                if isinstance(items, list) and items:
                    print(f'  İlk item keys: {list(items[0].keys())[:8]}')
                    p0 = items[0]
                    print(f'  İlk ürün: {p0.get("name","?")} — {p0.get("price","?")}')
    except Exception as e:
        print(f'  productState parse FAIL: {e}')
else:
    print('productState bulunamadı')

# li parser zaten çalışıyor — confirm
from bs4 import BeautifulSoup as BS
soup2 = BS(html2, 'html.parser')
cards = soup2.select('li[class^="productListContent-"]')
print(f'\nli[class^=productListContent-]: {len(cards)} kart BULUNDU')
if cards:
    # İlk kart fiyat ve isim
    c0 = cards[0]
    name_el = c0.find(['h3','h2','span'], attrs={'class': lambda x: x and ('name' in ' '.join(x).lower() or 'title' in ' '.join(x).lower())})
    price_el = c0.find(attrs={'class': lambda x: x and 'price' in ' '.join(x).lower() if x else False})
    print(f'  Kart[0] name_el: {name_el.get_text()[:60] if name_el else "?"}')
    print(f'  Kart[0] price_el: {price_el.get_text()[:40] if price_el else "?"}')
    # data attribute
    data_attrs = {k:v for k,v in c0.attrs.items() if 'data' in k}
    print(f'  data attrs: {data_attrs}')
