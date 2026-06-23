"""
Turkanime.tv sitemap.xml.gz indir, tum slug-baslik listesini cikar.
"""
import urllib.request
import gzip
import re
import json
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
    'Accept': '*/*',
}

def fetch_gz(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read()
        return gzip.decompress(data).decode('utf-8', errors='replace')
    except Exception as e:
        return f'HATA: {e}'

all_slugs = {}  # slug -> url

for i in range(1, 4):
    url = f'https://www.turkanime.tv/sitemap/tv/sitemap{i}.xml.gz'
    print(f'Indiriliyor: {url}')
    xml = fetch_gz(url)
    if xml.startswith('HATA'):
        print(f'  {xml}')
        continue

    # <loc> URL'leri bul
    locs = re.findall(r'<loc>(https://www\.turkanime\.tv/[^<]+)</loc>', xml)

    # /video/ URL'lerini filtrele (bunlar anime episode sayfaları)
    video_slugs = []
    for loc in locs:
        # /video/some-slug-1-bolum veya /video/some-slug (no ep number)
        m = re.search(r'/video/(.+?)(?:-\d+-bolum)?$', loc)
        if m and '/video/' in loc:
            slug = m.group(1)
            # ep numarası sonuna eklenmemis slug'ları kaydet
            # ya da -bolum varsa bu bir video
            if '-bolum' in loc:
                # slug = loc kismindaki slug-{N}-bolum'dan slug'ı cıkar
                m2 = re.search(r'/video/(.+?)-\d+-bolum', loc)
                if m2:
                    slug = m2.group(1)
            else:
                slug = m.group(1)

            if slug not in all_slugs:
                all_slugs[slug] = loc
                video_slugs.append(slug)

    print(f'  {len(locs)} loc, {len(video_slugs)} yeni video slug')
    time.sleep(0.5)

print(f'\nToplam benzersiz slug: {len(all_slugs)}')
print('\nOrnek sluglar (ilk 30):')
for slug in list(all_slugs.keys())[:30]:
    print(f'  {slug}')

# JSON olarak kaydet
out = '/mnt/c/Kuroshin/scripts/turkanime_slugs.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(list(all_slugs.keys()), f, ensure_ascii=False, indent=2)
print(f'\nKaydedildi: {out}')
