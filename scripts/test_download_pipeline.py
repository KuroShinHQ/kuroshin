"""
scripts/test_download_pipeline.py
"İndir butonuna basınca ne olur?" simülasyonu — disk'e yazmaz.

Anime (tranimaci.com + turkanime.tv) + Manga pipeline testi.

Çalıştır: python3.11 scripts/test_download_pipeline.py
"""

import asyncio
import sqlite3
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, "/mnt/c/Kuroshin/kurowatch")

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "text/html,*/*"}


# ── Yardımcılar ──────────────────────────────────────────────────────

def http_head(url: str) -> tuple[bool, int]:
    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status == 200, r.status
    except urllib.error.HTTPError as e:
        return False, e.code
    except Exception:
        return False, 0


def yt_dlp_simulate(url: str) -> tuple[bool, str]:
    try:
        res = subprocess.run(
            ["yt-dlp", "--simulate", "--no-warnings", "-q", url],
            capture_output=True, text=True, timeout=30
        )
        if res.returncode == 0:
            return True, "simulate OK"
        err = (res.stderr or res.stdout or "").strip()
        return False, err[:100] if err else f"exit {res.returncode}"
    except subprocess.TimeoutExpired:
        return False, "yt-dlp timeout"
    except FileNotFoundError:
        return False, "yt-dlp yok"


async def find_stream(url: str, timeout: int = 40) -> tuple[str, bool]:
    """find_stream_url çalıştır, gerçek URL bulundu mu?"""
    from backend.downloader.stream_finder import find_stream_url
    try:
        result = await asyncio.wait_for(find_stream_url(url), timeout=timeout)
        return result, result != url
    except asyncio.TimeoutError:
        return url, False
    except Exception as e:
        return f"HATA:{e}", False


# ── Manga chapter test ────────────────────────────────────────────────

def test_manga_url(url: str) -> tuple[bool, str]:
    """Madara /?style=list ile sayfa içerik kontrolü."""
    from urllib.parse import urlparse
    import re

    _MADARA = ("ragnarscans.com", "mangawow.com", "manhwahentai.me")
    domain = urlparse(url).netloc.lstrip("www.")

    if any(domain.endswith(m) for m in _MADARA):
        list_url = url.rstrip("/") + "/?style=list"
        req = urllib.request.Request(list_url, headers=HEADERS)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            if resp.status != 200:
                return False, f"HTTP {resp.status}"
            html = resp.read().decode("utf-8", errors="replace")
            imgs = re.findall(r'(?:data-src|src)=["\']([^"\']*\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', html, re.I)
            imgs = [i for i in imgs if not any(s in i for s in ("logo","favicon","banner","icon","themes"))]
            if imgs:
                return True, f"{len(imgs)} görsel bulundu ✅"
            return True, "200 OK (JS lazy-load, erişilebilir)"
        except Exception as e:
            return False, str(e)[:80]

    # MangaDex vb.
    ok, code = http_head(url)
    return ok, f"HEAD {code}"


# ── Ana test ─────────────────────────────────────────────────────────

async def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 65)
    print("KuroWatch — İndirme Pipeline Simülasyonu")
    print("=" * 65)

    # ── 1. Anime (tranimaci.com) ──────────────────────────────────────
    print("\n[1/3] ANİME — tranimaci.com (Playwright stream finder)")
    cur.execute("""
        SELECT c.id, c.title, e.number, e.url
        FROM episode e JOIN content c ON e.content_id=c.id
        WHERE c.type='anime' AND e.number=1
          AND e.url LIKE '%tranimaci.com%'
        ORDER BY RANDOM() LIMIT 2
    """)
    anime_rows = cur.fetchall()

    anime_results = []
    for cid, title, ep, url in anime_rows:
        t0 = time.time()
        print(f"\n  [{cid}] {title[:40]} ep-{ep}")
        print(f"  URL: {url}")
        stream_url, stream_ok = await find_stream(url, timeout=35)
        elapsed = round(time.time() - t0, 1)

        ytdlp_ok = False
        ytdlp_detail = "—"
        if stream_ok:
            ytdlp_ok, ytdlp_detail = yt_dlp_simulate(stream_url)

        status = "✅ ÇALIŞIYOR" if ytdlp_ok else ("⚠️ STREAM YOK" if not stream_ok else "❌ YT-DLP HATA")
        print(f"  Stream: {'bulundu' if stream_ok else 'BULUNAMADI (orijinal döndü)'}")
        if stream_ok:
            print(f"  Stream URL: {stream_url[:80]}")
            print(f"  yt-dlp simulate: {ytdlp_detail}")
        print(f"  Sonuç: {status} ({elapsed}s)")
        anime_results.append(ytdlp_ok)

    # ── 2. Anime (turkanime.tv) ───────────────────────────────────────
    print("\n[2/3] ANİME — turkanime.tv (site URL'den test)")
    cur.execute("""
        SELECT co.id, co.title, s.site_url FROM site s
        JOIN content co ON s.content_id=co.id
        WHERE co.type='anime' AND s.site_url LIKE '%turkanime.tv%'
        ORDER BY RANDOM() LIMIT 2
    """)
    tv_rows = cur.fetchall()

    tv_results = []
    for cid, title, url in tv_rows:
        t0 = time.time()
        print(f"\n  [{cid}] {title[:40]}")
        print(f"  URL: {url}")
        stream_url, stream_ok = await find_stream(url, timeout=50)
        elapsed = round(time.time() - t0, 1)

        ytdlp_ok = False
        ytdlp_detail = "—"
        if stream_ok:
            ytdlp_ok, ytdlp_detail = yt_dlp_simulate(stream_url)

        status = "✅ ÇALIŞIYOR" if ytdlp_ok else ("⚠️ STREAM YOK" if not stream_ok else "❌ YT-DLP HATA")
        print(f"  Stream: {'bulundu → ' + stream_url[:70] if stream_ok else 'BULUNAMADI'}")
        if stream_ok:
            print(f"  yt-dlp simulate: {ytdlp_detail}")
        print(f"  Sonuç: {status} ({elapsed}s)")
        tv_results.append(ytdlp_ok)

    # ── 3. Manga/Manhwa ───────────────────────────────────────────────
    print("\n[3/3] MANGA/MANHWA — Madara chapter testi")
    cur.execute("""
        SELECT c.id, c.title, c.type, e.number, e.url
        FROM episode e JOIN content c ON e.content_id=c.id
        WHERE c.type IN ('manga','manhwa') AND e.number=1
          AND e.url IS NOT NULL
        ORDER BY RANDOM() LIMIT 3
    """)
    manga_rows = cur.fetchall()

    manga_results = []
    for cid, title, ctype, ep, url in manga_rows:
        ok, detail = test_manga_url(url)
        status = "✅ ÇALIŞIYOR" if ok else "❌ ERİŞİLEMEZ"
        print(f"  {status} [{cid}] {ctype} | {title[:35]} | {detail}")
        manga_results.append(ok)

    conn.close()

    # ── GENEL ÖZET ────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("ÖZET")
    print("=" * 65)

    def result_str(results):
        ok = sum(results)
        t = len(results)
        return f"{ok}/{t} {'✅' if ok == t else ('⚠️' if ok > 0 else '❌')}"

    print(f"  Anime tranimaci.com  : {result_str(anime_results)}")
    print(f"  Anime turkanime.tv   : {result_str(tv_results)}")
    print(f"  Manga/Manhwa         : {result_str(manga_results)}")

    all_ok = all(anime_results + tv_results + manga_results)
    any_ok = any(anime_results + tv_results + manga_results)

    print()
    if all_ok:
        print("✅ TÜM TESTLER GEÇTİ — Download butonu çalışıyor.")
    elif any_ok:
        print("⚠️  KISMI SONUÇ — Bazı içerik türleri çalışıyor, bazıları değil.")
    else:
        print("❌ HİÇBİR TEST GEÇMEDI.")


if __name__ == "__main__":
    asyncio.run(main())
