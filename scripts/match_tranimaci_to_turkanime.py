"""
tranimaci.com animelerini turkanime.tv slug'larıyla eslestir.

1. Tam eslestirme (slug = slug)
2. Prefix eslestirme (tranimaci slug ilk 3 kelime turkanime slug prefix'i)
3. Kelime kesisimi (ortak kelime sayisi yuksek olan)
"""
import sqlite3
import re
import json

DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
SLUGS_FILE = '/mnt/c/Kuroshin/scripts/turkanime_slugs.json'

with open(SLUGS_FILE, encoding='utf-8') as f:
    turk_slugs = set(json.load(f))

conn = sqlite3.connect(DB)
c = conn.cursor()

# tranimaci animeleri ve slug'lari
c.execute("""
    SELECT DISTINCT c.id, c.title, e.url
    FROM content c
    JOIN episode e ON e.content_id = c.id
    WHERE e.url LIKE '%tranimaci%'
    ORDER BY c.title
""")
rows = c.fetchall()

# Her anime icin slug al
anime_slugs = {}  # content_id -> (title, tranimaci_slug)
for cid, title, url in rows:
    if cid not in anime_slugs:
        m = re.search(r'/video/(.+?)-\d+-bolum', url)
        slug = m.group(1) if m else None
        anime_slugs[cid] = (title, slug)

def slug_words(slug):
    return set(slug.split('-')) if slug else set()

tam = []      # (cid, title, tranimaci_slug, turkanime_slug)
onerilen = [] # (cid, title, tranimaci_slug, turkanime_slug, puan)
eslesmedi = []

for cid, (title, tslug) in anime_slugs.items():
    if not tslug:
        eslesmedi.append((cid, title, tslug, []))
        continue

    # 1. Tam eslesme
    if tslug in turk_slugs:
        tam.append((cid, title, tslug, tslug))
        continue

    # 2. Kelime kesisimi - en iyi adayi bul
    t_words = slug_words(tslug)
    if not t_words:
        eslesmedi.append((cid, title, tslug, []))
        continue

    best_slug = None
    best_score = 0
    candidates = []

    for ts in turk_slugs:
        ts_words = slug_words(ts)
        # Kesisim orani
        common = len(t_words & ts_words)
        if common >= 2:
            # Jaccard benzerligi
            union = len(t_words | ts_words)
            score = common / union if union > 0 else 0
            # Prefix bonus
            if ts.startswith(tslug[:min(len(tslug), 15)]):
                score += 0.3
            candidates.append((score, ts))

    if candidates:
        candidates.sort(reverse=True)
        top = candidates[:3]
        best_score, best_slug = top[0]
        if best_score >= 0.4:
            onerilen.append((cid, title, tslug, best_slug, round(best_score, 2)))
        else:
            eslesmedi.append((cid, title, tslug, [t[1] for t in top[:2]]))
    else:
        eslesmedi.append((cid, title, tslug, []))

SEP = '='*100
print(SEP)
print(f'TAM ESLESME ({len(tam)} adet):')
print(SEP)
for cid, title, ts, tk in sorted(tam, key=lambda x: x[1]):
    print(f'  ID={cid:4} | {str(title)[:40]:40} | {ts} -> {tk}')

print()
print(SEP)
print(f'FUZZY ESLESME - KONTROL GEREKLI ({len(onerilen)} adet):')
print(SEP)
for cid, title, ts, tk, score in sorted(onerilen, key=lambda x: -x[4]):
    mark = 'OK' if score >= 0.6 else '?? '
    print(f'  {mark} ID={cid:4} | {str(title)[:35]:35} | tranimaci: {ts[:35]:35} -> turk: {tk} (puan={score})')

print()
print(SEP)
print(f'ESLESMEDI ({len(eslesmedi)} adet - turkanime.tv yok veya cok farkli slug):')
print(SEP)
for cid, title, tslug, alts in sorted(eslesmedi, key=lambda x: x[1]):
    alt_str = ' | alts: ' + ', '.join(alts) if alts else ''
    print(f'  ID={cid:4} | {str(title)[:40]:40} | {tslug}{alt_str}')

print(f'\nOZET: tam={len(tam)} | fuzzy={len(onerilen)} | yok={len(eslesmedi)}')

# Guvenliligi yuksek onerileri kaydet
guvenli = tam + [(c, t, ts, tk, 1.0) for c, t, ts, tk in tam]
guvenli_fuzzy = [(cid, title, ts, tk) for cid, title, ts, tk, score in onerilen if score >= 0.6]
print(f'Guvenligi yuksek fuzzy esleme (>=0.6): {len(guvenli_fuzzy)}')

conn.close()
