"""
Broken içerikleri çalışan kaynaklarla eşleştirip DB'yi günceller.
Bölüm 1: Anime → turkanime.tv index araması
"""
import sqlite3, json, re
from pathlib import Path
from difflib import SequenceMatcher

DB   = Path("/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db")
TA   = Path("/mnt/c/Kuroshin/kurowatch/scripts/ta_index.json")

# ── Yardımcılar ──────────────────────────────────────────────────────────────
def slug(text):
    t = text.lower()
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'\s+', '-', t.strip())
    return t

def normalize(text):
    t = text.lower()
    # parantez kaldır
    t = re.sub(r'\(.*?\)', '', t)
    # noktalama kaldır
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

# ── Turkanime index yükle ─────────────────────────────────────────────────────
with open(TA) as f:
    ta_index = json.load(f)  # slug → url

# index'i normalize isim → (slug, url) olarak da tut
ta_norm = {}
for slug_key, url in ta_index.items():
    norm = re.sub(r'[^a-z0-9 ]', ' ', slug_key.replace('-', ' ')).strip()
    ta_norm[norm] = (slug_key, url)

# ── DB: broken anime listesi ──────────────────────────────────────────────────
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

DEAD_NAMES = {'tranimeizle', 'tranimeizle.io', 'İzle', 'Seri', 'Link'}

cur.execute('''
    SELECT c.id, c.title, c.type,
           GROUP_CONCAT(s.site_name || '::' || s.is_dead, '|') as sites
    FROM content c
    LEFT JOIN site s ON s.content_id = c.id
    WHERE c.type = 'anime'
    GROUP BY c.id
''')

broken_anime = []
for r in cur.fetchall():
    sites = r['sites'] or ''
    has_ok = False
    for part in sites.split('|'):
        if '::' in part:
            name, dead = part.split('::', 1)
            if not (dead == '1') and name not in DEAD_NAMES:
                has_ok = True
                break
    if not has_ok:
        broken_anime.append({'id': r['id'], 'title': r['title']})

print(f"Broken anime sayısı: {len(broken_anime)}")

# ── Turkanime eşleştirme ──────────────────────────────────────────────────────
# Bilinen non-turkanime (western içerik) — bunları atla
WESTERN_KEYWORDS = [
    'breaking bad', 'game of thrones', 'rick and morty', 'the walking dead',
    'mr robot', 'hannibal', 'you joe', 'love death', 'la casa', 'sherlock',
    'doctor who', 'dark 2017', 'dark ', 'black mirror', 'mentalist',
    'batman', 'spider-man', 'avengers', 'thor', 'iron man', 'deadpool', 'venom',
    'captain america', 'doctor strange', 'marvel',
    'ben 10', 'tom and jerry', 'looney tunes', 'scooby-doo', 'powerpuff',
    'adventure time', 'regular show', 'gumball', 'gravity falls', 'steven universe',
    'teen titans', 'uncle grandpa', 'clarence', 'we bare bears', 'ninjago',
    'phineas', 'totally spies', 'kim possible', 'american dragon', 'johnny bravo',
    'justice league', 'megas xlr', 'generator rex', 'transformers', 'sonic',
    'bakugan', 'ed edd', 'max steel', 'samurai jack', 'dexter lab',
    'winnie the pooh', 'yogi bear', 'mickey mouse',
    'titanic', 'inception', 'matrix', 'john wick', 'fight club', 'godfather',
    'harry potter', 'hobbit', 'lord of the rings', 'hunger games', 'maze runner',
    'pacific rim', 'terminator', 'resident evil', 'world war z',
    'toy story', 'finding nemo', 'incredibles', 'shrek', 'madagaskar', 'kung fu panda',
    'ice age', 'up ', 'cars ', 'lion king', 'shark tale', 'corpse bride',
    'wall-e', 'alvin', 'percy jackson', 'twilight',
    'adanali', 'arka sokaklar', 'sihirli annem', 'yaprak dokumu', 'seksenler',
    'kurtlar vadisi', 'genis aile', 'pis yedili', 'selena ', 'yahsi cazibe',
    'doktorlar', 'muhtesem yuzyil', 'galip dervish',
    'gora', 'kolpacino', 'recep ivedik', 'hababam', 'hacivat', 'maskeli besler',
    'cem yilmaz', 'yahsi bati', 'dugun dernek', 'behzat',
    'fetih 1453', '300 spartali', 'gladiator', 'gladio', 'filistin',
    'la casa de papel', 'limitless', 'the mentalist',
    'planet of the apes', 'twilight', 'dabbe serisi', 'abimm',
    'dragonsf', 'dreamworks dragons', 'total drama', 'flapjack',
    'disney broken', 'broken karaoke', 'space goofs', 'hugo',
]

def is_western(title):
    t = title.lower()
    for kw in WESTERN_KEYWORDS:
        if kw in t:
            return True
    return False

found = []
not_found = []
skipped_western = []

for item in broken_anime:
    title = item['title']
    content_id = item['id']

    if is_western(title):
        skipped_western.append(title)
        continue

    # Turkanime slug dene
    norm_title = normalize(title)

    # 1. Direkt slug dene
    candidate_slug = slug(title)
    if candidate_slug in ta_index:
        url = ta_index[candidate_slug]
        found.append({'id': content_id, 'title': title, 'url': url, 'method': 'direct'})
        continue

    # 2. Normalize karşılaştırma (similarity)
    best_score = 0
    best_match = None
    for norm_key, (sl, url) in ta_norm.items():
        score = similarity(norm_title, norm_key)
        if score > best_score:
            best_score = score
            best_match = (sl, url, score)

    if best_score > 0.7:
        found.append({'id': content_id, 'title': title, 'url': best_match[1],
                     'method': f'fuzzy({best_score:.2f})', 'matched_slug': best_match[0]})
    else:
        not_found.append({'id': content_id, 'title': title,
                         'best': best_match[0] if best_match else None, 'score': best_score})

print(f"\nSonuçlar:")
print(f"  Western (atlandı): {len(skipped_western)}")
print(f"  Turkanime'de bulundu: {len(found)}")
print(f"  Bulunamadı: {len(not_found)}")

print("\n=== TURKANIME'DE BULUNANLAR ===")
for f in found:
    print(f"  [id={f['id']}] {f['title']}")
    print(f"    → {f['url']}  ({f['method']})")
    if 'matched_slug' in f:
        print(f"    matched: {f['matched_slug']}")

print("\n=== BULUNAMAYANLAR (non-western) ===")
for nf in not_found:
    print(f"  [id={nf['id']}] {nf['title']}")
    if nf['best']:
        print(f"    en yakın: {nf['best']} (skor: {nf['score']:.2f})")

# ── DB güncelle ───────────────────────────────────────────────────────────────
print("\n=== DB GÜNCELLEME (dry-run) ===")
print("Onaylamak için: fix_broken_sources.py --apply yazın\n")

import sys
if '--apply' in sys.argv:
    added = 0
    for f in found:
        # Önce bu içerik için mevcut turkanime girişi var mı?
        cur.execute("SELECT id FROM site WHERE content_id=? AND site_name='turkanime.tv'", (f['id'],))
        existing = cur.fetchone()
        if existing:
            print(f"  SKIP (zaten var): {f['title']}")
            continue
        cur.execute("""
            INSERT INTO site (content_id, site_name, site_url, is_primary, is_dead)
            VALUES (?, 'turkanime.tv', ?, 0, 0)
        """, (f['id'], f['url']))
        added += 1
        print(f"  ADDED: {f['title']} → {f['url']}")
    conn.commit()
    print(f"\nEklendi: {added}")
