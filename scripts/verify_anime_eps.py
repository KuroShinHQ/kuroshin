"""
tranimaci.com'da DB'deki episode numaralarini dogrula
"""
import urllib.request, sqlite3

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

# content_id → tranimaci slug mapping
SLUG_MAP = {
    96:  "dungeon-meshi",
    592: "saihate-no-paladin",
    638: "uncle-from-another-world",
    678: "bakis-path-2-kisim",  # Baki's Path 2. Kisim
}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for cid, slug in SLUG_MAP.items():
    cur.execute("SELECT number FROM episode WHERE content_id=? ORDER BY number", (cid,))
    ep_nums = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT title FROM content WHERE id=?", (cid,))
    title = cur.fetchone()[0]

    print(f"\n[{cid}] {title} - {len(ep_nums)} ep")

    # Her ep'i test et (max 5 - örnekleme)
    test_nums = ep_nums if len(ep_nums) <= 5 else [ep_nums[0], ep_nums[len(ep_nums)//4], ep_nums[len(ep_nums)//2], ep_nums[-1]]

    ok = 0
    fail = 0
    for n in test_nums:
        url = f"https://www.tranimaci.com/video/{slug}-{n}-bolum"
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=12)
            print(f"  OK  {resp.status} ep-{n}")
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"  ERR {e.code} ep-{n} — {url}")
            fail += 1
        except Exception as ex:
            print(f"  EXC ep-{n}: {ex}")
            fail += 1

    print(f"  => Sonuc: {ok} OK / {fail} FAIL (ornek {len(test_nums)}/{len(ep_nums)})")

conn.close()
