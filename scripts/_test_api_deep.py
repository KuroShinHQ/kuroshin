"""
Trendyol ve HB HTML'inde gömülü JSON veri yapısını bul
"""
import re, json, sys
sys.path.insert(0, '/mnt/c/Kuroshin/scripts')

try:
    import curl_cffi.requests as req
except ImportError:
    import requests as req

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
}

# ─── TRENDYOL ────────────────────────────────────────────────────────────────
print('=' * 60)
print('TRENDYOL — JSON yapısı arama')
print('=' * 60)

r = req.get('https://www.trendyol.com/sr?q=kondisyon+bisikleti&pi=1', impersonate='chrome124', timeout=20, headers=H)
html = r.text
print(f'HTML: {len(html):,}c')

# Tüm <script> taglerini bul
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f'Script tag sayısı: {len(scripts)}')

json_scripts = []
for i, s in enumerate(scripts):
    s = s.strip()
    if s.startswith('{') or s.startswith('['):
        json_scripts.append((i, s))
        try:
            d = json.loads(s)
            print(f'  Script[{i}] JSON parse OK — type={type(d).__name__} keys={list(d.keys())[:5] if isinstance(d, dict) else len(d)}')
        except:
            pass

# brandName yakınındaki veri
brand_positions = [m.start() for m in re.finditer(r'"brandName"', html)]
print(f'\nbrandName konumları: {len(brand_positions)}')
if brand_positions:
    # İlk eşleşmeyi çöz
    pos = brand_positions[0]
    ctx = html[max(0, pos-200):pos+500]
    # JSON obje sınırını bul
    print(f'İlk brandName çevresi:\n{ctx[:600]}')

# Trendyol'un window.productCards veya benzeri
patterns = [
    r'window\.__productCards\s*=\s*([\[\{].*?)(?:;\s*</script>|;\s*window\.)',
    r'"productCard"\s*:\s*(\{[^{}]{50,}?\})',
    r'"products"\s*:\s*(\[.*?\])',
    r'data-productid="(\d+)"',
    r'"contentDescriptions"\s*:\s*(\[.*?\])',
]
for p in patterns:
    m = re.search(p, html, re.DOTALL)
    if m:
        print(f'\nPATTERN BULUNDU: {p[:40]}')
        print(f'  {m.group(1)[:300]}')
    else:
        print(f'Pattern yok: {p[:40]}')

# ─── HEPSİBURADA ─────────────────────────────────────────────────────────────
print('\n' + '=' * 60)
print('HEPSİBURADA — veri yapısı arama')
print('=' * 60)

r2 = req.get('https://www.hepsiburada.com/ara?q=kondisyon+bisikleti', impersonate='chrome124', timeout=20, headers=H)
html2 = r2.text
print(f'HTML: {len(html2):,}c')

# HB'de bilinen SSR pattern
hb_patterns = [
    r'li\[class\^="productListContent',
    r'class="productListContent-',
    r'data-productid',
    r'"sku"\s*:\s*"([^"]+)"',
    r'"price"\s*:\s*(\d+)',
    r'window\.__INITIAL_STATE__',
    r'window\.__data',
]
for p in hb_patterns:
    matches = re.findall(p, html2[:200000])
    print(f'HB pattern "{p[:35]}": {len(matches)} buldu {matches[:3]}')

# HB script'leri
hb_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html2, re.DOTALL)
for i, s in enumerate(hb_scripts[:20]):
    s = s.strip()
    if len(s) > 200 and ('price' in s.lower() or 'product' in s.lower()):
        print(f'\nHB Script[{i}] ({len(s)}c) ilginç:')
        print(s[:400])
        break

print('\nTEST TAMAM')
