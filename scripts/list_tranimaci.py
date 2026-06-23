import sqlite3

DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# Kolon isimlerini goster
c.execute("PRAGMA table_info(content)")
cols = [r[1] for r in c.fetchall()]
print('content kolonlari:', cols)

c.execute("PRAGMA table_info(episode)")
ecols = [r[1] for r in c.fetchall()]
print('episode kolonlari:', ecols)

c.execute("""
SELECT DISTINCT c.id, c.title, e.url
FROM content c
JOIN episode e ON e.content_id = c.id
WHERE e.url LIKE '%tranimaci%'
ORDER BY c.title
""")
rows = c.fetchall()

seen = {}
for r in rows:
    if r[0] not in seen:
        seen[r[0]] = r

print(f'\nToplam tranimaci anime: {len(seen)}')
for cid, (rid, ttitle, url) in sorted(seen.items(), key=lambda x: x[1][1] or ''):
    print(f'  ID={rid:4} | {str(ttitle)[:40]:40} | {str(url)[:65]}')

c.execute("SELECT COUNT(*) FROM episode WHERE url LIKE '%tranimaci%'")
print(f'\nToplam tranimaci episode: {c.fetchone()[0]}')
conn.close()
