"""
Trendyol HTML içindeki gömülü JSON'dan ürün çekme testi
curl_cffi ile fetch → regex ile JSON bul → parse et
Playwright YOK, ML YOK
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
    'Accept': 'text/html,application/xhtml+xml,*/*',
}

def fetch_trendyol_products(query: str, budget: float = 99999) -> list:
    url = f'https://www.trendyol.com/sr?q={query.replace(" ", "+")}&pi=1'
    r = req.get(url, impersonate='chrome124', timeout=20, headers=H)

    if r.status_code != 200:
        print(f'FAIL: {r.status_code}')
        return []

    html = r.text

    # Gömülü "products" JSON array bul
    m = re.search(r'"products"\s*:\s*(\[.*?\])\s*,\s*"(?:productCount|totalCount|pagination)', html, re.DOTALL)
    if not m:
        # Alternatif pattern
        m = re.search(r'"products"\s*:\s*(\[.{100,}?\])', html, re.DOTALL)

    if not m:
        print('products JSON bulunamadı')
        return []

    try:
        products_raw = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        # JSON kırık olabilir, önce düzelt
        raw = m.group(1)
        print(f'JSON parse hatası: {e} — raw uzunluk: {len(raw)}')
        return []

    results = []
    for p in products_raw:
        try:
            name_parts = []
            cf = p.get('cleanUrlFragments', {})
            brand = cf.get('webBrandName') or p.get('brand', '')
            name = cf.get('name') or p.get('name', '')

            if not name:
                continue

            # Fiyat
            price_raw = p.get('price', {})
            if isinstance(price_raw, dict):
                price = price_raw.get('discountedPrice', {}).get('value') or \
                        price_raw.get('originalPrice', {}).get('value') or 0
            else:
                price = float(price_raw) if price_raw else 0

            # Alternatif fiyat alanı
            if not price:
                disc = p.get('discountedPrice', '')
                if disc:
                    price_str = re.sub(r'[^\d,]', '', str(disc)).replace(',', '.')
                    try:
                        price = float(price_str)
                    except:
                        pass

            # Yorum
            rating = p.get('ratingScore', {})
            if isinstance(rating, dict):
                score = rating.get('averageRating', 0)
                count = rating.get('totalCount', 0)
            else:
                score, count = 0, 0

            # URL
            url_slug = p.get('url', '')
            product_url = f'https://www.trendyol.com{url_slug}' if url_slug else ''

            results.append({
                'brand': brand,
                'name': name,
                'price': price,
                'rating': score,
                'review_count': count,
                'url': product_url,
            })
        except Exception as e:
            pass

    return results


# ─── TEST ────────────────────────────────────────────────────────────────────
print('Trendyol JSON fetch testi — kondisyon bisikleti')
products = fetch_trendyol_products('kondisyon bisikleti', budget=5000)

print(f'\nToplam ürün: {len(products)}')
for i, p in enumerate(products[:10], 1):
    price_str = f"{p['price']:,.0f} TL" if p['price'] else 'fiyat yok'
    rating_str = f"⭐{p['rating']:.1f}({p['review_count']})" if p['rating'] else 'yorum yok'
    print(f'  {i}. [{p["brand"]}] {p["name"][:60]} — {price_str} {rating_str}')

if products:
    prices = [p['price'] for p in products if p['price'] > 0]
    print(f'\nFiyat aralığı: {min(prices):.0f} — {max(prices):.0f} TL')
    print(f'Fiyatı olan ürün: {len(prices)}/{len(products)}')
    print('\n✅ Trendyol JSON parse BAŞARILI — Playwright gerekmiyor!')
else:
    print('\n❌ Ürün bulunamadı')
