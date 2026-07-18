"""
KuroWatch — Tüm içerik URL keşif + ping testi
497 anime + 163 manga/manhwa — paralel HEAD isteği ile hangi sitelerde mevcut?

Çıktı: scripts/ping_results.json + terminal özet
Çalıştır: python3 scripts/ping_all_content.py
"""
import sqlite3, urllib.request, urllib.error, re, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unicodedata import normalize

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"
OUT_PATH = "/mnt/c/Kuroshin/scripts/ping_results.json"
MAX_WORKERS = 20
TIMEOUT = 8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

# --- Site tanımları ---
MANGA_SITES = [
    ("ragnarscans.com", "manga"),
    ("mangawow.com",    "manga"),
    ("manhwahentai.me", "manhwa"),
    ("merlintoon.com",  "manga"),
    ("mangadenizi.com", "manga"),
]

ANIME_SITES = [
    ("www.tranimaci.com", "anime"),
    ("www.turkanime.co",  "anime"),
]

# --- Slug üretici ---
TR_MAP = str.maketrans("üöığşçÜÖIĞŞÇ", "uoigscoOIGSC")

def slugify(text):
    t = text.lower().translate(TR_MAP)
    t = normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    t = re.sub(r"[\s_]+", "-", t.strip())
    t = re.sub(r"-+", "-", t)
    return t.strip("-")

def candidate_urls(title, title_tr, ctype):
    slugs = [slugify(title)]
    if title_tr:
        s2 = slugify(title_tr)
        if s2 != slugs[0]:
            slugs.append(s2)
    # Parantez içini kaldır (kısa versiyon)
    short = re.sub(r"\s*\(.*?\)", "", title).strip()
    if short != title:
        slugs.append(slugify(short))

    sites = ANIME_SITES if ctype == "anime" else MANGA_SITES
    urls = []
    for slug in slugs[:2]:  # max 2 slug dene
        for site, path in sites:
            urls.append((site, slug, f"https://{site}/{path}/{slug}/"))
    return urls

# --- HTTP testi ---
def ping(url):
    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0  # timeout/DNS/etc

def test_content(row):
    cid, title, title_tr, ctype = row
    candidates = candidate_urls(title, title_tr, ctype)
    for site, slug, url in candidates:
        code = ping(url)
        if code == 200:
            return {"id": cid, "title": title, "type": ctype,
                    "status": "OK", "site": site, "slug": slug, "url": url}
    return {"id": cid, "title": title, "type": ctype,
            "status": "NOT_FOUND", "site": None, "slug": None, "url": None}

# --- Ana akış ---
def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.title, c.title_tr, c.type
        FROM content c
        WHERE c.type IN ('anime', 'manga', 'manhwa')
        ORDER BY c.type, c.id
    """)
    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    print(f"Toplam test edilecek: {total} içerik ({MAX_WORKERS} paralel)")
    print(f"{'='*60}")

    results = []
    ok = 0
    fail = 0
    done = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(test_content, row): row for row in rows}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            done += 1
            if res["status"] == "OK":
                ok += 1
                print(f"  ✅ [{res['id']:4}] {res['type']:7} {res['title'][:35]:35} → {res['site']}")
            else:
                fail += 1
                if done % 50 == 0 or done == total:
                    elapsed = time.time() - start
                    print(f"  ... {done}/{total} ({elapsed:.0f}s) — {ok} OK / {fail} FAIL")

    # JSON'a kaydet
    results.sort(key=lambda r: (r["type"], r["status"], r["id"]))
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"ÖZET: {ok} OK / {fail} NOT_FOUND / {total} toplam ({elapsed:.0f}s)")
    print(f"Sonuçlar: {OUT_PATH}")

    # Tip bazında özet
    from collections import Counter
    by_type = {}
    for r in results:
        t = r["type"]
        if t not in by_type:
            by_type[t] = {"ok": 0, "fail": 0}
        if r["status"] == "OK":
            by_type[t]["ok"] += 1
        else:
            by_type[t]["fail"] += 1
    print("\nTip özeti:")
    for t, v in sorted(by_type.items()):
        print(f"  {t:8}: {v['ok']:3} OK / {v['fail']:3} FAIL")

    # Site dağılımı
    site_counts = Counter(r["site"] for r in results if r["site"])
    print("\nSite dağılımı:")
    for site, cnt in site_counts.most_common():
        print(f"  {cnt:4} {site}")

if __name__ == "__main__":
    run()
