"""
scripts/migrate_to_turkanime.py
tranimaci.com episode URL'lerini turkanime.tv'ye migrate et.

Strateji:
  1. tranimaci.com episode'u olan her anime icin slug al (mevcut URL'den)
  2. turkanime.tv/video/{slug}-1-bolum → HEAD test
  3. 200 OK → tum episode URL'lerini turkanime.tv olarak guncelle (veya ekle)
  4. 404 → atla, raporda listele

Calistir:
  python3 scripts/migrate_to_turkanime.py           # canli mod
  python3 scripts/migrate_to_turkanime.py --dry-run # DB'ye yazmadan rapor
  python3 scripts/migrate_to_turkanime.py --limit 20 # ilk 20 anime test et
"""

import sqlite3
import re
import sys
import time
import urllib.request
import urllib.error

DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
TRANIMACI_BASE = 'https://www.tranimaci.com/video'
TURKANIME_BASE = 'https://www.turkanime.tv/video'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
    'Accept': 'text/html,*/*',
    'Accept-Language': 'tr-TR,tr;q=0.9',
}

DRY_RUN = '--dry-run' in sys.argv
LIMIT = None
for a in sys.argv:
    if a.startswith('--limit='):
        LIMIT = int(a.split('=')[1])

def head_ok(url: str, timeout: int = 8) -> bool:
    req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False

def extract_slug(url: str) -> str | None:
    """tranimaci.com/video/some-slug-3-bolum → 'some-slug'"""
    m = re.search(r'/video/(.+?)-(\d+)-bolum', url)
    return m.group(1) if m else None

def run():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # tranimaci.com episode'u olan animeleri bul
    c.execute("""
        SELECT DISTINCT c.id, c.title, c.total_episodes
        FROM content c
        JOIN episode e ON e.content_id = c.id
        WHERE e.url LIKE '%tranimaci%'
        ORDER BY c.title
    """)
    animeler = c.fetchall()

    if LIMIT:
        animeler = animeler[:LIMIT]

    print(f"tranimaci.com animesi: {len(animeler)} | DRY_RUN={DRY_RUN}\n")
    print(f"{'ID':>5}  {'Baslik':<38}  {'Slug':<45}  Sonuc")
    print('-' * 110)

    eslesti = []    # (content_id, title, slug, total_eps)
    eslesmedi = []  # (content_id, title, slug)
    slug_yok = []   # (content_id, title)

    for cid, title, total_eps in animeler:
        # Mevcut tranimaci URL'sinden slug al
        c.execute("SELECT url FROM episode WHERE content_id=? AND url LIKE '%tranimaci%' LIMIT 1", (cid,))
        row = c.fetchone()
        if not row:
            slug_yok.append((cid, title))
            print(f"{cid:>5}  {str(title)[:38]:<38}  {'???':<45}  ⚠ ep yok")
            continue

        slug = extract_slug(row[0])
        if not slug:
            slug_yok.append((cid, title))
            print(f"{cid:>5}  {str(title)[:38]:<38}  {'???':<45}  ⚠ slug cikarilmadi")
            continue

        # turkanime.tv'de test et
        test_url = f"{TURKANIME_BASE}/{slug}-1-bolum"
        ok = head_ok(test_url)
        time.sleep(0.3)  # rate limit

        if ok:
            eslesti.append((cid, title, slug, total_eps))
            print(f"{cid:>5}  {str(title)[:38]:<38}  {slug:<45}  ✅ OK")
        else:
            eslesmedi.append((cid, title, slug))
            print(f"{cid:>5}  {str(title)[:38]:<38}  {slug:<45}  ❌ 404")

    print(f"\n{'='*110}")
    print(f"✅ eslesti     : {len(eslesti)}")
    print(f"❌ eslesmedi   : {len(eslesmedi)}")
    print(f"⚠  slug yok   : {len(slug_yok)}")

    if DRY_RUN:
        print("\n[DRY-RUN] DB guncellemesi yapilmadi.")
        if eslesmedi:
            print(f"\neslesmeyenler ({len(eslesmedi)}):")
            for cid, title, slug in eslesmedi:
                print(f"  ID={cid:4} | {title[:40]} | denenen: {slug}")
        conn.close()
        return

    # DB guncelle
    updated_eps = 0
    updated_anime = 0
    for cid, title, slug, total_eps in eslesti:
        total = total_eps or 0

        # Mevcut tranimaci episode'larini sil
        c.execute("DELETE FROM episode WHERE content_id=? AND url LIKE '%tranimaci%'", (cid,))
        deleted = c.rowcount

        # Mevcut turkanime episode'lari var mi kontrol et
        c.execute("SELECT number FROM episode WHERE content_id=? AND url LIKE '%turkanime%'", (cid,))
        existing_turk = {r[0] for r in c.fetchall()}

        # Yeni episode'lari ekle (total_episodes kadar)
        if total > 0:
            new_rows = []
            for n in range(1, int(total) + 1):
                if n not in existing_turk:
                    new_rows.append((cid, 1, n, f"{TURKANIME_BASE}/{slug}-{n}-bolum", 0, 0))

            if new_rows:
                c.executemany(
                    "INSERT OR IGNORE INTO episode (content_id, season, number, url, is_watched, is_new) VALUES (?,?,?,?,?,?)",
                    new_rows
                )
                updated_eps += len(new_rows)
        else:
            # total_episodes bilinmiyor, sadece slug'i site tablosuna yaz
            pass

        # Site tablosunu da guncelle
        c.execute(
            "UPDATE site SET site_url=? WHERE content_id=? AND site_url LIKE '%tranimaci%'",
            (f"{TURKANIME_BASE}/{slug}-1-bolum", cid)
        )

        updated_anime += 1

    conn.commit()
    print(f"\n✅ {updated_anime} anime guncellendi, {updated_eps} yeni turkanime.tv episode eklendi")

    if eslesmedi:
        print(f"\nDikkat — {len(eslesmedi)} anime turkanime.tv'de bulunamadi (tranimaci'de kaldi):")
        for cid, title, slug in eslesmedi[:20]:
            print(f"  ID={cid:4} | {title[:45]}")
        if len(eslesmedi) > 20:
            print(f"  ... ve {len(eslesmedi)-20} tane daha")

    conn.close()

if __name__ == '__main__':
    run()
