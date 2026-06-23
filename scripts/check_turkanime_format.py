import sqlite3

DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# Mevcut turkanime.tv episode URL ornekleri
c.execute("""
SELECT c.id, c.title, e.url
FROM content c JOIN episode e ON e.content_id = c.id
WHERE e.url LIKE '%turkanime%'
ORDER BY RANDOM()
LIMIT 15
""")
rows = c.fetchall()
print('turkanime.tv URL ornekleri:')
for r in rows:
    print(f'  ID={r[0]:4} | {str(r[1])[:35]:35} | {r[2]}')

# Site tablosunda turkanime.tv listing URL var mi?
c.execute("""
SELECT content_id, site_url
FROM site
WHERE site_url LIKE '%turkanime%'
LIMIT 10
""")
rows2 = c.fetchall()
print(f'\nSite tablosu turkanime.tv ({len(rows2)} ornek):')
for r in rows2:
    print(f'  ID={r[0]:4} | {r[1]}')

conn.close()
