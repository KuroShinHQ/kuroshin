"""
Her manga/manhwa icerigi icin 1 chapter URL HEAD testi
"""
import urllib.request, sqlite3

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""
    SELECT c.id, c.title, e.number, e.url
    FROM content c
    JOIN episode e ON c.id = e.content_id
    WHERE c.type IN ('manga', 'manhwa', 'manhua')
    AND e.number = (SELECT MIN(number) FROM episode WHERE content_id=c.id)
    ORDER BY c.id
""")
rows = cur.fetchall()
conn.close()

ok_count = 0
fail_count = 0
for cid, title, num, url in rows:
    req = urllib.request.Request(url, headers=headers, method="HEAD")
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        print(f"OK  {resp.status} [{cid}] {title} (bolum-{num})")
        ok_count += 1
    except urllib.error.HTTPError as e:
        print(f"ERR {e.code} [{cid}] {title} (bolum-{num}) -> {url}")
        fail_count += 1
    except Exception as ex:
        print(f"EXC [{cid}] {title}: {ex}")
        fail_count += 1

print(f"\nSonuc: {ok_count} OK / {fail_count} FAIL")
