"""
Download URL Saglik Operasyonu - DB Guncelleme
- Nano Machine (content_id=18): mangasehri.net -> ragnarscans.com/manga/nano-makine/
- Buyu Imparatoru (content_id=4): uzaymanga.com -> ragnarscans.com/manga/buyu-imparatoru/
"""
import sqlite3

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"

UPDATES = [
    {
        "content_id": 18,
        "title": "Nano Machine",
        "slug": "nano-makine",
        "site": "ragnarscans.com",
        "old_domain": "mangasehri.net",
    },
    {
        "content_id": 4,
        "title": "Buyu Imparatoru",
        "slug": "buyu-imparatoru",
        "site": "ragnarscans.com",
        "old_domain": "uzaymanga.com",
    },
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for item in UPDATES:
    cid = item["content_id"]
    slug = item["slug"]
    site = item["site"]

    # Mevcut episode'lari al
    cur.execute("SELECT id, number FROM episode WHERE content_id=?", (cid,))
    episodes = cur.fetchall()

    updated = 0
    for ep_id, number in episodes:
        new_url = f"https://{site}/manga/{slug}/bolum-{number}/"
        cur.execute("UPDATE episode SET url=? WHERE id=?", (new_url, ep_id))
        updated += 1

    conn.commit()
    print(f"[OK] {item['title']} (content_id={cid}): {updated} episode guncellendi")
    print(f"     Yeni URL formati: https://{site}/manga/{slug}/bolum-N/")

# Dogrulama
print("\n=== Dogrulama ===")
for item in UPDATES:
    cid = item["content_id"]
    cur.execute("SELECT number, url FROM episode WHERE content_id=? ORDER BY number LIMIT 3", (cid,))
    rows = cur.fetchall()
    print(f"\n{item['title']} (ilk 3 episode):")
    for num, url in rows:
        print(f"  bolum-{num}: {url}")
    cur.execute("SELECT COUNT(*) FROM episode WHERE content_id=? AND url LIKE ?",
                (cid, f"%{item['old_domain']}%"))
    remaining = cur.fetchone()[0]
    print(f"  Kalan eski URL: {remaining}")

conn.close()
print("\nTamam.")
