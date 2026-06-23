"""
scripts/bulk_episode_sync.py
Tüm anime için tranimaci.com episode URL'lerini DB'ye yükle.

Kaynak önceliği:
  1. ping_results.json → 497 anime slug (onceki ping testi)
  2. Site tablosu tranimaci.com video URL → slug çıkar (37 anime)
  3. Site tablosu listing URL → slug çıkar + ep testi (yeni kartlar)
  4. Hiçbiri → atla

Episode URL format: https://www.tranimaci.com/video/{slug}-{N}-bolum

Çalıştır:
  python3 scripts/bulk_episode_sync.py
  python3 scripts/bulk_episode_sync.py --dry-run   # DB'ye yazmadan raporla
  python3 scripts/bulk_episode_sync.py --verify    # Sonunda 20 URL testi yap
"""

import sqlite3
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from unicodedata import normalize

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"
PING_JSON = "/mnt/c/Kuroshin/scripts/ping_results.json"
BASE = "https://www.tranimaci.com/video"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

DRY_RUN = "--dry-run" in sys.argv
VERIFY  = "--verify"  in sys.argv

# ── Yardımcılar ──────────────────────────────────────────────────────

TR_MAP = str.maketrans("üöığşçÜÖIĞŞÇ", "uoigscoOIGSC")

def slugify(text: str) -> str:
    t = text.lower().translate(TR_MAP)
    t = normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    t = re.sub(r"[\s_]+", "-", t.strip())
    return re.sub(r"-+", "-", t).strip("-")


def extract_slug_from_video_url(url: str) -> str | None:
    """
    https://tranimaci.com/video/some-slug-12-bolum → 'some-slug'
    https://tranimaci.com/video/some-slug-3-bolum  → 'some-slug'
    """
    m = re.search(r"/video/(.+?)-\d+-bolum", url)
    return m.group(1) if m else None


def extract_slug_from_listing_url(url: str) -> str | None:
    """https://www.tranimaci.com/anime/some-slug/ → 'some-slug'"""
    m = re.search(r"/anime/([^/]+)/?$", url)
    return m.group(1) if m else None


def ep_url(slug: str, n: int) -> str:
    return f"{BASE}/{slug}-{n}-bolum"


def http_ok(url: str, timeout: int = 6) -> bool:
    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False

# ── Ana akış ─────────────────────────────────────────────────────────

def run():
    # 1. ping_results.json yükle
    ping_map: dict[int, str] = {}
    if Path(PING_JSON).exists():
        with open(PING_JSON, encoding="utf-8") as f:
            for r in json.load(f):
                if r.get("type") == "anime" and r.get("status") == "OK" and r.get("slug"):
                    ping_map[r["id"]] = r["slug"]
    print(f"ping_results.json: {len(ping_map)} anime slug yüklendi")

    # 2. DB bağlantısı
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 2a. Tüm anime
    cur.execute(
        "SELECT id, title, total_episodes FROM content WHERE type='anime' ORDER BY id"
    )
    all_anime = cur.fetchall()  # [(id, title, total_episodes), ...]

    # 2b. Site URL'leri
    cur.execute("SELECT content_id, site_url FROM site WHERE is_primary=1")
    site_map: dict[int, str] = {row[0]: row[1] for row in cur.fetchall()}

    # 2c. Mevcut episode'lar (content_id → set of numbers)
    cur.execute("SELECT content_id, number FROM episode")
    existing: dict[int, set] = {}
    for cid, num in cur.fetchall():
        existing.setdefault(cid, set()).add(num)

    # 3. Her anime için slug belirle
    slug_map: dict[int, str] = {}
    skipped_no_slug: list = []
    skipped_listing: list = []

    for cid, title, total_eps in all_anime:
        # Önce ping
        if cid in ping_map:
            slug_map[cid] = ping_map[cid]
            continue

        # Sonra site URL
        site_url = site_map.get(cid, "") or ""
        slug = extract_slug_from_video_url(site_url)
        if slug:
            slug_map[cid] = slug
            continue

        # Listing URL'den çıkar (doğrulama gerektirir)
        slug = extract_slug_from_listing_url(site_url)
        if slug:
            skipped_listing.append((cid, title, total_eps, slug))
            continue

        skipped_no_slug.append((cid, title, site_url))

    print(f"\nSlug kaynağı özeti:")
    print(f"  ping_results     : {sum(1 for c in all_anime if c[0] in ping_map)}")
    site_only = len([c for c in all_anime if c[0] not in ping_map and c[0] in slug_map])
    print(f"  site video URL   : {site_only}")
    print(f"  listing URL (test gerekli) : {len(skipped_listing)}")
    print(f"  slug YOK (atlandı)         : {len(skipped_no_slug)}")

    # Listing URL'leri için slug doğrulama (HTTP HEAD /video/{slug}-1-bolum)
    if skipped_listing:
        print(f"\nListing slug'ları doğrulanıyor ({len(skipped_listing)} adet)...")
        verified = 0
        for cid, title, total_eps, slug in skipped_listing:
            test = ep_url(slug, 1)
            if http_ok(test):
                slug_map[cid] = slug
                verified += 1
            else:
                skipped_no_slug.append((cid, title, f"listing slug '{slug}' 404"))
        print(f"  {verified}/{len(skipped_listing)} listing slug doğrulandı")

    # 4. Episode kayıtları oluştur
    new_eps: list[tuple] = []  # (content_id, number, url)
    synced_anime = 0
    already_done = 0
    no_total = 0

    for cid, title, total_eps in all_anime:
        slug = slug_map.get(cid)
        if not slug:
            continue

        total = total_eps or 0
        if total <= 0:
            no_total += 1
            continue

        exist = existing.get(cid, set())
        if len(exist) >= total:
            already_done += 1
            continue

        added = 0
        for n in range(1, int(total) + 1):
            if n not in exist:
                new_eps.append((cid, n, ep_url(slug, n)))
                added += 1

        if added > 0:
            synced_anime += 1

    print(f"\nEpisode özeti:")
    print(f"  {synced_anime} anime için yeni episode oluşturulacak")
    print(f"  {sum(1 for c in all_anime if c[0] in slug_map and (c[2] or 0) > 0)} anime toplam slug+total var")
    print(f"  {already_done} anime zaten tamamdı")
    print(f"  {no_total} anime total_episodes=0 (atlandı)")
    print(f"  Toplam yeni episode: {len(new_eps)}")

    if DRY_RUN:
        print("\n[DRY-RUN] DB'ye yazılmadı. Örnek URL'ler:")
        for cid, n, url in new_eps[:10]:
            title = next(a[1] for a in all_anime if a[0] == cid)
            print(f"  ID={cid} | {title[:30]} | ep{n} → {url}")
        conn.close()
        return

    # 5. DB'ye yaz
    if new_eps:
        cur.executemany(
            "INSERT OR IGNORE INTO episode (content_id, season, number, url, is_watched, is_new) "
            "VALUES (?, 1, ?, ?, 0, 0)",
            [(cid, n, url) for cid, n, url in new_eps]
        )
        conn.commit()
        print(f"\n✅ {len(new_eps)} episode DB'ye kaydedildi")
    else:
        print("\nYeni episode yok.")

    # Son durum
    cur.execute("SELECT COUNT(DISTINCT content_id) FROM episode WHERE content_id IN (SELECT id FROM content WHERE type='anime')")
    final_anime = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM episode WHERE content_id IN (SELECT id FROM content WHERE type='anime')")
    final_eps = cur.fetchone()[0]
    print(f"DB durumu: {final_anime} anime, {final_eps} toplam anime episode")

    # 6. Verify: 20 rastgele episode URL'si test et
    if VERIFY:
        print("\n── Verify: 20 rastgele anime episode URL testi ──")
        import random
        cur.execute(
            "SELECT e.content_id, c.title, e.number, e.url "
            "FROM episode e JOIN content c ON e.content_id=c.id "
            "WHERE c.type='anime' AND e.number=1 AND e.url LIKE '%tranimaci%' "
            "ORDER BY RANDOM() LIMIT 20"
        )
        rows = cur.fetchall()
        ok = 0
        for cid, title, num, url in rows:
            result = http_ok(url)
            status = "✅" if result else "❌"
            if result:
                ok += 1
            print(f"  {status} ID={cid} | {title[:35]} | {url}")
        print(f"\nSonuç: {ok}/{len(rows)} URL 200 OK")

    conn.close()


if __name__ == "__main__":
    run()
