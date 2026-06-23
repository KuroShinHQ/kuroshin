import sqlite3
DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# type dagılımı
c.execute("""
SELECT c.type, COUNT(DISTINCT c.id)
FROM content c
JOIN episode e ON e.content_id = c.id
WHERE e.url LIKE '%tranimaci%'
GROUP BY c.type
""")
print('tranimaci animeleri type dagılımı:')
for r in c.fetchall():
    print(f'  type={r[0]:15} | {r[1]} adet')

# type='anime' olanlar
c.execute("""
SELECT DISTINCT c.id, c.title, e.url
FROM content c
JOIN episode e ON e.content_id = c.id
WHERE e.url LIKE '%tranimaci%' AND c.type='anime'
ORDER BY c.title
""")
rows = c.fetchall()
seen = {}
for r in rows:
    if r[0] not in seen:
        seen[r[0]] = (r[1], r[2])
print(f'\ntype=anime tranimaci icerikleri ({len(seen)} adet):')
for cid, (title, url) in sorted(seen.items(), key=lambda x: x[1][0]):
    m = __import__('re').search(r'/video/(.+?)-\d+-bolum', url)
    slug = m.group(1) if m else '???'
    print(f'  ID={cid:4} | {str(title)[:45]:45} | {slug}')

conn.close()
