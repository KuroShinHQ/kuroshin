"""
Trendyol — JSON boundaries doğru bul
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

r = req.get('https://www.trendyol.com/sr?q=kondisyon+bisikleti&pi=1', impersonate='chrome124', timeout=20, headers=H)
html = r.text
print(f'HTML: {len(html):,}c')

# "products" nerede başlıyor?
pos = html.find('"products":')
print(f'"products" pozisyonu: {pos}')
if pos < 0:
    print('products bulunamadı'); sys.exit(1)

# Bracket counting — doğru JSON array sınırı
def extract_json_array(text, start_pos):
    """JSON array başladığı yerden bracket sayarak sonu bul."""
    i = text.find('[', start_pos)
    if i < 0:
        return None, -1
    depth = 0
    in_string = False
    escape = False
    for j in range(i, len(text)):
        c = text[j]
        if escape:
            escape = False
            continue
        if c == '\\' and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                return text[i:j+1], j+1
    return None, -1

raw_array, end = extract_json_array(html, pos)
if not raw_array:
    print('Array sınırı bulunamadı'); sys.exit(1)

print(f'Array uzunluğu: {len(raw_array):,}c')
print(f'İlk 300c: {raw_array[:300]}')

try:
    products = json.loads(raw_array)
    print(f'\nJSON parse OK — {len(products)} ürün')
except json.JSONDecodeError as e:
    print(f'JSON parse hatası: {e}')
    # Hata pozisyonunu göster
    err_pos = e.pos
    print(f'Hata çevresi: ...{raw_array[max(0,err_pos-100):err_pos+100]}...')
    sys.exit(1)

# Ürünleri göster
print(f'\n--- İLK 10 ÜRÜN ---')
for i, p in enumerate(products[:10], 1):
    cf = p.get('cleanUrlFragments', {})
    brand = cf.get('webBrandName', p.get('brand', '?'))
    name = cf.get('name', p.get('name', '?'))

    # Fiyat — Trendyol farklı yapıda olabilir
    price = 0
    price_obj = p.get('price', {})
    if isinstance(price_obj, dict):
        price = (price_obj.get('discountedPrice') or
                 price_obj.get('sellingPrice') or
                 price_obj.get('originalPrice') or 0)
        if isinstance(price, dict):
            price = price.get('value', 0)

    # Alternatif: discountedPriceNumerized
    if not price:
        price = p.get('discountedPriceNumerized', 0) or p.get('priceNumerized', 0)

    rating_obj = p.get('ratingScore', {})
    rating = rating_obj.get('averageRating', 0) if isinstance(rating_obj, dict) else 0
    count = rating_obj.get('totalCount', 0) if isinstance(rating_obj, dict) else 0

    print(f'  {i}. [{brand}] {str(name)[:60]}')
    print(f'     Fiyat: {price} | ⭐{rating}({count})')
    print(f'     Tüm keys: {list(p.keys())[:10]}')

# Fiyat field'larını keşfet
print(f'\n--- FİYAT ALANLARI (ilk ürün) ---')
if products:
    p0 = products[0]
    for k, v in p0.items():
        if 'price' in k.lower() or 'fiyat' in k.lower():
            print(f'  {k}: {v}')
