import sqlite3, json, re
from pathlib import Path
from difflib import SequenceMatcher

DB   = Path('/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db')
HAM  = Path('/mnt/c/Kuroshin/kurowatch/docs/hamjsondata.md')

DEAD = {'MangaTR','MangaTR.me','mangatr','MangaOkuTR','mangaokutr','tranimeizle',
        'tranimeizle.io','İzle','Seri','Link','W2 Site','UzayManga','RüyaManga',
        'MangaŞehri','MangaKoleji','MangaTepesi','TürkManga','TürkçeMangaOku',
        'GölgeBahçesi','MajorScans','TempestFansub','ArcaneScans','AsuraScans',
        'MerlinScans','MerlinToon'}

def normalize(title):
    t = title.lower()
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# 1. hamjsondata.md parse
lines = HAM.read_text(encoding='utf-8').splitlines()
items = []
depth = 0
buf = []
for line in lines:
    stripped = line.strip()
    if stripped == '[' and depth == 0:
        depth = 1; buf = ['[']; continue
    if depth > 0:
        depth += stripped.count('[') - stripped.count(']')
        if depth == 0:
            buf.append(']')
            try:
                parsed = json.loads('\n'.join(buf))
                for obj in parsed:
                    if isinstance(obj, dict):
                        items.append(obj)
            except:
                pass
            buf = []
        else:
            buf.append(line)

TARGET_TYPES = {'anime', 'manga', 'manhwa'}
ham_singles = []
for it in items:
    typ = it.get('type','').lower().strip()
    if typ not in TARGET_TYPES:
        continue
    title = it.get('title','').strip()
    if not title or ' / ' in title:
        continue
    ham_singles.append({'title': title, 'type': typ,
                        'status': it.get('status',''),
                        'rating': it.get('personal_rating','')})

seen = set()
ham_dedup = []
for it in ham_singles:
    k = normalize(it['title'])
    if k not in seen:
        seen.add(k)
        ham_dedup.append(it)

print(f'Ham tekil anime/manga/manhwa (grup hariç): {len(ham_dedup)}')

# 2. DB
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('''
    SELECT c.id, c.title, c.type,
           GROUP_CONCAT(s.site_name || '::' || s.is_dead, '|') as sites
    FROM content c
    LEFT JOIN site s ON s.content_id = c.id
    WHERE c.type IN ('anime','manga','manhwa')
    GROUP BY c.id
''')

db_items = {}
for r in cur.fetchall():
    sites_str = r['sites'] or ''
    parts = [p for p in sites_str.split('|') if '::' in p]
    has_ok = any(
        d != '1' and n not in DEAD
        for p in parts
        for n, d in [p.rsplit('::', 1)]
    )
    db_items[normalize(r['title'])] = {'title': r['title'], 'has_ok': has_ok, 'type': r['type']}
conn.close()

# 3. Eşleştir
matched_ok = []
matched_broken = []
not_in_db = []

for ham_it in ham_dedup:
    norm = normalize(ham_it['title'])
    if norm in db_items:
        if db_items[norm]['has_ok']:
            matched_ok.append((ham_it['title'], ham_it['type']))
        else:
            matched_broken.append((ham_it['title'], ham_it['type']))
        continue
    best = None; best_score = 0
    for db_norm, db_it in db_items.items():
        score = SequenceMatcher(None, norm, db_norm).ratio()
        if score > best_score:
            best_score = score; best = db_it
    if best_score > 0.75:
        if best['has_ok']:
            matched_ok.append((ham_it['title'], ham_it['type']))
        else:
            matched_broken.append((ham_it['title'], ham_it['type']))
    else:
        not_in_db.append((ham_it['title'], ham_it['type']))

total = len(ham_dedup)
pct_ok = round(len(matched_ok) / total * 100, 1)

print(f'\n=== SONUC ===')
print(f'Toplam ham tekil: {total}')
print(f'Indirilebilir (calisan kaynak): {len(matched_ok)} -- %{pct_ok}')
print(f'Kaynak broken/yok: {len(matched_broken)}')
print(f'DB eslesme yok: {len(not_in_db)}')

print(f'\n--- Broken (ham listesinde olan) ---')
for title, typ in sorted(matched_broken, key=lambda x: x[1]):
    print(f'  [{typ}] {title}')

print(f'\n--- DB eslesmesi olmayan ---')
for title, typ in sorted(not_in_db, key=lambda x: x[1]):
    print(f'  [{typ}] {title}')
