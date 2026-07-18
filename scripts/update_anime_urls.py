"""
Anime URL Sagligi - tranimeizle.co/io → tranimaci.com
"""
import sqlite3

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"

UPDATES = [
    {"content_id": 96,  "title": "Dungeon Meshi",             "slug": "dungeon-meshi"},
    {"content_id": 592, "title": "Faraway Paladin",            "slug": "saihate-no-paladin"},
    {"content_id": 638, "title": "Uncle from Another World",   "slug": "uncle-from-another-world"},
    {"content_id": 678, "title": "Baki's Path 2. Kisim",       "slug": "bakis-path-2-kisim"},
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for item in UPDATES:
    cid = item["content_id"]
    slug = item["slug"]

    cur.execute("SELECT id, number FROM episode WHERE content_id=?", (cid,))
    episodes = cur.fetchall()

    updated = 0
    for ep_id, number in episodes:
        new_url = f"https://www.tranimaci.com/video/{slug}-{number}-bolum"
        cur.execute("UPDATE episode SET url=? WHERE id=?", (new_url, ep_id))
        updated += 1

    conn.commit()
    print(f"[OK] {item['title']} (content_id={cid}): {updated} episode guncellendi")
    print(f"     Yeni format: https://www.tranimaci.com/video/{slug}-N-bolum")

# Dogrulama
print("\n=== Dogrulama ===")
for item in UPDATES:
    cid = item["content_id"]
    cur.execute("SELECT number, url FROM episode WHERE content_id=? ORDER BY number LIMIT 2", (cid,))
    rows = cur.fetchall()
    print(f"\n{item['title']}:")
    for num, url in rows:
        print(f"  ep-{num}: {url}")
    cur.execute("SELECT COUNT(*) FROM episode WHERE content_id=? AND url LIKE '%tranimeizle%'", (cid,))
    remaining = cur.fetchone()[0]
    print(f"  Kalan eski URL: {remaining}")

conn.close()
print("\nTamam.")
