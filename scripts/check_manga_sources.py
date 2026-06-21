"""
Broken manga/manhwa için çalışan URL'leri MangaGezgini ve MangaWow'da arar.
"""
import urllib.request, re, time, sqlite3, json
from pathlib import Path

DB = Path('/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}

def try_url(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = r.read(2000).decode('utf-8', errors='ignore')
            # 404 sayfası döndürüyor ama 200 status veriyor olabilir
            if '404' in content[:500] and 'Not Found' in content[:500]:
                return False
            return r.status == 200
    except:
        return False

def to_slug(title):
    t = title.lower()
    t = re.sub(r'\(.*?\)', '', t)    # parantez kaldır
    t = re.sub(r"[']", '', t)         # apostrof
    t = re.sub(r'[^\w\s-]', ' ', t)  # noktalama → boşluk
    t = re.sub(r'\s+', '-', t.strip())
    t = re.sub(r'-+', '-', t)
    return t.strip('-')

# Alternatif slug'lar
def slug_variants(title):
    variants = []
    base = to_slug(title)
    variants.append(base)
    # "The " prefix kaldır
    if base.startswith('the-'):
        variants.append(base[4:])
    # Subtitle kaldır (: sonrası)
    if ':' in title:
        short = to_slug(title.split(':')[0].strip())
        variants.append(short)
    # Parantez içerikleri dahil
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', title).strip()
    if clean != title:
        variants.append(to_slug(clean))
    return list(dict.fromkeys(variants))  # dedup

SITES = [
    ('MangaGezgini', 'https://mangagezgini.com/manga/{slug}/'),
    ('MangaWow', 'https://mangawow.com/manga/{slug}/'),
]

# Broken manga/manhwa listesi DB'den çek
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

DEAD_NAMES = {'MangaTR', 'MangaTR.me', 'mangatr', 'MangaOkuTR', 'mangaokutr',
              'tranimeizle', 'tranimeizle.io', 'İzle', 'Seri', 'Link', 'W2 Site',
              'UzayManga', 'RüyaManga', 'MangaŞehri', 'MangaKoleji', 'MangaTepesi',
              'TürkManga', 'TürkçeMangaOku', 'GölgeBahçesi', 'MajorScans',
              'TempestFansub', 'ArcaneScans', 'AsuraScans', 'MerlinScans', 'MerlinToon'}

cur.execute('''
    SELECT c.id, c.title, c.type,
           GROUP_CONCAT(s.site_name || '::' || s.is_dead, '|') as sites
    FROM content c
    LEFT JOIN site s ON s.content_id = c.id
    WHERE c.type IN ('manga', 'manhwa')
    GROUP BY c.id
''')

broken = []
for r in cur.fetchall():
    sites = r['sites'] or ''
    has_ok = any(
        not (d == '1') and n not in DEAD_NAMES
        for part in sites.split('|')
        for n, d in [part.split('::', 1)] if '::' in part
    )
    if not has_ok:
        broken.append({'id': r['id'], 'title': r['title'], 'type': r['type']})

conn.close()
print(f"Kontrol edilecek manga/manhwa: {len(broken)}\n")

found = []
not_found = []

for i, item in enumerate(broken):
    title = item['title']
    cid = item['id']
    variants = slug_variants(title)

    hit = None
    for site_name, url_tmpl in SITES:
        for slug in variants:
            url = url_tmpl.format(slug=slug)
            if try_url(url):
                hit = (site_name, url)
                break
        if hit:
            break

    if hit:
        found.append({'id': cid, 'title': title, 'site': hit[0], 'url': hit[1]})
        print(f"[{i+1}/{len(broken)}] ✅ {title}")
        print(f"         → {hit[1]}")
    else:
        not_found.append({'id': cid, 'title': title})
        print(f"[{i+1}/{len(broken)}] ❌ {title}")

    time.sleep(0.4)  # site'yi spam etme

print(f"\n{'='*50}")
print(f"BULUNDU: {len(found)} | BULUNAMADI: {len(not_found)}")
print(f"{'='*50}")

# Sonuçları kaydet
results = {'found': found, 'not_found': not_found}
out = Path('/mnt/c/Kuroshin/scripts/manga_source_results.json')
out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(f"\nSonuçlar kaydedildi: {out}")
