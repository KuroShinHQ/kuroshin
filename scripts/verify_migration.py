import sqlite3, urllib.request, urllib.error

DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
HEADERS = {'User-Agent': 'Mozilla/5.0 Chrome/120.0', 'Accept': 'text/html,*/*'}

conn = sqlite3.connect(DB)
c = conn.cursor()

# Migrated animelerden ep-1 URL'leri al
c.execute("""
    SELECT c.title, e.url
    FROM content c JOIN episode e ON e.content_id = c.id
    WHERE e.url LIKE '%turkanime%'
      AND e.number = 1
      AND c.id IN (687,690,715,710,709,695,704,698,686,361,697,701,714,707,683,682)
    ORDER BY c.title
""")
rows = c.fetchall()
conn.close()

ok = 0
fail = 0
for title, url in rows:
    req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
    try:
        resp = urllib.request.urlopen(req, timeout=8)
        status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        status = 0

    mark = '✅' if status == 200 else '❌'
    if status == 200:
        ok += 1
    else:
        fail += 1
    print(f'{mark} {status} | {str(title)[:40]:40} | {url}')

print(f'\nSonuc: {ok}/{ok+fail} OK')
