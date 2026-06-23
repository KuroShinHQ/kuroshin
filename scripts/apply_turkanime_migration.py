"""
tranimaci_to_turkanime_map.json kullanarak DB'yi guncelle.

Her eslesen anime icin:
  1. Tranimaci episode URL'lerini sil
  2. Turkanime.tv episode URL'lerini ekle (total_episodes kadar)
  3. Site tablosunu guncelle

Calistir:
  python3 scripts/apply_turkanime_migration.py           # canli mod
  python3 scripts/apply_turkanime_migration.py --dry-run
"""
import sqlite3, json, re, sys

DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
MAP_FILE = '/mnt/c/Kuroshin/scripts/tranimaci_to_turkanime_map.json'
TURK_BASE = 'https://www.turkanime.tv/video'
TRANI_BASE = 'https://www.tranimaci.com/video'

DRY = '--dry-run' in sys.argv

with open(MAP_FILE, encoding='utf-8') as f:
    slug_map = json.load(f)  # tranimaci_slug -> turkanime_slug

conn = sqlite3.connect(DB)
c = conn.cursor()

def extract_slug(url):
    m = re.search(r'/video/(.+?)-\d+-bolum', url)
    return m.group(1) if m else None

# Tranimaci animeleri ve slug'lari
c.execute("""
    SELECT DISTINCT c.id, c.title, c.total_episodes
    FROM content c
    JOIN episode e ON e.content_id = c.id
    WHERE e.url LIKE '%tranimaci%'
    ORDER BY c.title
""")
animeler = c.fetchall()

print(f'Tranimaci anime: {len(animeler)} | DRY_RUN={DRY}')
print()

updated_anime = 0
total_added = 0
total_deleted = 0
skipped = 0

for cid, title, total_eps in animeler:
    # Mevcut slug
    c.execute("SELECT url FROM episode WHERE content_id=? AND url LIKE '%tranimaci%' LIMIT 1", (cid,))
    row = c.fetchone()
    if not row:
        continue

    tslug = extract_slug(row[0])
    if not tslug:
        continue

    # Map'te var mi?
    turk_slug = slug_map.get(tslug)
    if not turk_slug:
        skipped += 1
        continue

    # Mevcut tranimaci episode sayisi
    c.execute("SELECT COUNT(*) FROM episode WHERE content_id=? AND url LIKE '%tranimaci%'", (cid,))
    trani_count = c.fetchone()[0]

    total = total_eps or 0
    turk_url_1 = f'{TURK_BASE}/{turk_slug}-1-bolum'

    print(f'ID={cid:4} | {str(title)[:40]:40} | {turk_slug} ({trani_count} ep, total={total})')

    if DRY:
        continue

    # 1. Tranimaci episode'lari sil
    c.execute("DELETE FROM episode WHERE content_id=? AND url LIKE '%tranimaci%'", (cid,))
    deleted = c.rowcount
    total_deleted += deleted

    # 2. Mevcut turkanime episode'lari kontrol et
    c.execute("SELECT number FROM episode WHERE content_id=? AND url LIKE '%turkanime%'", (cid,))
    existing_turk = {r[0] for r in c.fetchall()}

    # 3. Yeni episode'lar ekle
    if total > 0:
        new_rows = []
        for n in range(1, int(total) + 1):
            if n not in existing_turk:
                new_rows.append((cid, 1, n, f'{TURK_BASE}/{turk_slug}-{n}-bolum', 0, 0))
        if new_rows:
            c.executemany(
                "INSERT OR IGNORE INTO episode (content_id, season, number, url, is_watched, is_new) VALUES (?,?,?,?,?,?)",
                new_rows
            )
            total_added += len(new_rows)
    else:
        # total_episodes bilinmiyor, en az 1-bolum ekle
        if 1 not in existing_turk:
            c.execute(
                "INSERT OR IGNORE INTO episode (content_id, season, number, url, is_watched, is_new) VALUES (?,?,?,?,?,?)",
                (cid, 1, 1, turk_url_1, 0, 0)
            )
            total_added += 1

    # 4. Site tablosu guncelle
    c.execute(
        "UPDATE site SET site_url=? WHERE content_id=? AND site_url LIKE '%tranimaci%'",
        (turk_url_1, cid)
    )

    updated_anime += 1

if not DRY:
    conn.commit()
    print(f'\n{"="*70}')
    print(f'✅ {updated_anime} anime guncellendi')
    print(f'   {total_deleted} tranimaci episode silindi')
    print(f'   {total_added} turkanime.tv episode eklendi')
    print(f'   {skipped} anime map\'te yok (tranimaci\'de kaldi)')

    # Son durum
    c.execute("SELECT COUNT(*) FROM episode WHERE url LIKE '%tranimaci%'")
    remain_trani = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM episode WHERE url LIKE '%turkanime%'")
    total_turk = c.fetchone()[0]
    print(f'\nDB durumu:')
    print(f'  Kalan tranimaci episode: {remain_trani}')
    print(f'  Toplam turkanime.tv episode: {total_turk}')
else:
    print(f'\n[DRY-RUN] {skipped} anime map\'te yok, geri kalan tranimaci\'de kalacak.')

conn.close()
