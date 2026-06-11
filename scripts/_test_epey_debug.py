"""Epey parser debug — neden 0 ürün?"""
import sys, re
sys.path.insert(0, '/mnt/c/Kuroshin/scripts')
try:
    import curl_cffi.requests as req
except ImportError:
    import requests as req
from bs4 import BeautifulSoup

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Accept-Language': 'tr-TR,tr;q=0.9'}

r = req.get('https://www.epey.com/kondisyon-bisikleti/', impersonate='chrome131', timeout=20, headers=H)
html = r.text
soup = BeautifulSoup(html, 'html.parser')

# 1. #fiyatlar linkleri var mı?
price_links = soup.select('a[href*="#fiyatlar"]')
print(f'#fiyatlar link sayısı: {len(price_links)}')

if price_links:
    lnk = price_links[0]
    href = lnk.get('href','')
    text = lnk.get_text(' ', strip=True)
    print(f'İlk link href: {href}')
    print(f'İlk link text: "{text}"')

    # Slug
    slug = href.split('#')[0]
    print(f'Slug: {slug}')

    # Fiyat parse
    pm = re.search(r'([\d.]+),([\d]{2})\s*TL', text)
    pm2 = re.search(r'([\d.]+)\s*TL', text)
    print(f'Fiyat match (virgüllü): {pm}')
    print(f'Fiyat match (tam): {pm2}')
    if pm2:
        raw = pm2.group(1).replace('.','')
        print(f'Fiyat raw: {raw}')

    # İsim linki
    name_link = soup.find('a', href=lambda h: h and h.split('#')[0] == slug and '#' not in h)
    print(f'İsim linki: {name_link}')

    # Tüm linkleri slug ile ara
    all_links = soup.find_all('a', href=True)
    matches = [l for l in all_links if l.get('href','').split('#')[0] == slug]
    print(f'Slug eşleşen link sayısı: {len(matches)}')
    for m in matches[:3]:
        print(f'  href={m.get("href","")} text="{m.get_text()[:50]}"')
else:
    # Neden yok? HTML'e bak
    print('HATA: #fiyatlar linki YOK')
    # Tüm a href'leri
    all_a = soup.find_all('a', href=True)
    print(f'Toplam link: {len(all_a)}')
    fiyat_links = [a for a in all_a if 'fiyat' in a.get('href','').lower()]
    print(f'"fiyat" içeren link: {len(fiyat_links)}')
    for fl in fiyat_links[:5]:
        print(f'  {fl.get("href","")[:80]}')

    # Sayfa başlığı
    title = soup.find('title')
    print(f'Title: {title.get_text()[:80] if title else "yok"}')

    # HTML preview
    print(f'\nHTML ilk 2000c:\n{html[:2000]}')
