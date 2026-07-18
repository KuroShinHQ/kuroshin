"""
KuroWatch — Tüm içerik download başlatılabilirlik testi
Her içerik için ep-1 URL'sine test yapar (tam indirme YOK).

Madara manga : /?style=list → 200 + img bulunuyor mu?
gallery-dl   : --simulate ile extractor var mı?
Anime        : HEAD → 200 → OK
Turkanime    : HEAD → 200 (Playwright gerekir, sadece site erişimi)

Çalıştır:
  python3 scripts/test_all_downloads.py
  python3 scripts/test_all_downloads.py --fix   → FAIL URL'leri JSON olarak yaz
"""
import sqlite3, urllib.request, re, sys, subprocess, json, os
from urllib.parse import urlparse

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"
FAIL_OUT = "/mnt/c/Kuroshin/scripts/download_fails.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,*/*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
}

# manga.py ile AYNI olmalı — buradan güncelle, manga.py'ye yansıt
_MADARA_DOMAINS = {
    "mangawow.com", "mangawow.org",
    "hayalistic.com.tr",
    "ragnarscans.com", "ragnarscans.net",
    "merlintoon.com", "mangadenizi.com",
    "manhwahentai.me",
    # Eski (fallback için kalır)
    "manga-sehri.net", "mangakeyf.com", "mangahost.net",
    "okumangatr.com", "turkmanga.net", "mangaturk.org",
    "ruyamanga.com", "ruyamanga.net", "asurascans.com.tr",
}

_CF_BLOCKED = {
    "mangasehri.net", "mangasehri.com",
    "tranimeizle.co", "tranimeizle.io",
    "dizibox.so", "hdfilmcehennemi.nl",
}

_OFFLINE = {
    "mangaokutr.com", "mangatr.net",
    "majorscans.com", "majorscans.net",
}

_TURKANIME_PLAYWRIGHT = {"turkanime.tv"}  # Playwright şart, HEAD yeter


def domain_of(url):
    return urlparse(url).netloc.lstrip("www.")


def test_madara(url):
    list_url = url.rstrip("/") + "/?style=list"
    req = urllib.request.Request(list_url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        if resp.status != 200:
            return False, f"HTTP {resp.status}"
        html = resp.read().decode("utf-8", errors="replace")
        _SKIP = ("logo", "favicon", "banner", "avatar", "icon", "themes", "elementor", "spinner", "placeholder")
        imgs = [i for i in re.findall(
            r'(?:data-src|data-lazy-src|src)=["\']([^"\']*\.(?:jpg|jpeg|png|webp|avif)[^"\']*)["\']',
            html, re.IGNORECASE
        ) if not any(s in i.lower() for s in _SKIP)]
        if imgs:
            return True, f"{len(imgs)} img"
        return True, "200 OK (JS lazy)"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as ex:
        return False, str(ex)[:80]


def test_gallerydl(url):
    """gallery-dl --simulate ile extractor var mı kontrol et (hızlı, indirme yok)."""
    try:
        proc = subprocess.run(
            ["gallery-dl", "--simulate", "--no-download", url],
            capture_output=True, text=True, timeout=20
        )
        if proc.returncode == 0:
            return True, "gallery-dl OK"
        # exit 64 = NoExtractorError
        if proc.returncode == 64:
            return False, "gallery-dl NoExtractor (exit 64)"
        stderr = (proc.stderr or "").strip()[:80]
        return False, f"gallery-dl exit {proc.returncode}: {stderr}"
    except FileNotFoundError:
        return False, "gallery-dl bulunamadı (PATH'e ekle)"
    except subprocess.TimeoutExpired:
        return True, "gallery-dl timeout (büyük ihtimal çalışıyor)"
    except Exception as ex:
        return False, str(ex)[:80]


def test_head(url):
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers=HEADERS, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=12)
            return resp.status < 400, f"{method} {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code == 405 and method == "HEAD":
                continue
            return False, f"HTTP {e.code}"
        except Exception as ex:
            return False, str(ex)[:80]
    return False, "Bağlantı kurulamadı"


def test_url(url, content_type):
    if not url or not isinstance(url, str) or url.strip() == "":
        return False, "URL BOŞ"

    d = domain_of(url)

    if any(d.endswith(x) for x in _CF_BLOCKED):
        return False, f"CF_BLOCKED"

    if any(d.endswith(x) for x in _OFFLINE):
        return False, f"OFFLINE"

    if "mangadex.org" in url:
        return test_head(url)  # MangaDex API direkt çalışır

    if any(d.endswith(x) for x in _TURKANIME_PLAYWRIGHT):
        ok, det = test_head(url)
        return ok, f"[Playwright] {det}"

    if any(d.endswith(md) for md in _MADARA_DOMAINS):
        return test_madara(url)

    # Bilinmeyen → gallery-dl simulate
    if content_type in ("manga", "manhwa", "manhua"):
        return test_gallerydl(url)

    # Anime bilinmeyen site → HEAD
    return test_head(url)


def run():
    fix_mode = "--fix" in sys.argv

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.title, c.type,
               e.number, e.url
        FROM content c
        JOIN episode e ON c.id = e.content_id
        WHERE e.number = (SELECT MIN(number) FROM episode WHERE content_id = c.id)
        ORDER BY c.type, c.id
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("Hiç episodeli içerik bulunamadı.")
        return

    print(f"{'ID':>4} {'Tür':8} {'İçerik Adı':40} {'Ep':>4} {'Sonuç':6} {'Detay'}")
    print("-" * 100)

    ok_count = 0
    fail_count = 0
    fails = []

    for cid, title, ctype, ep_num, url in rows:
        ok, detail = test_url(url, ctype)
        status = "✅" if ok else "❌"
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            fails.append({
                "id": cid, "title": title, "type": ctype,
                "ep": ep_num, "url": url, "error": detail
            })
        print(f"{cid:>4} {ctype:8} {title[:40]:40} {ep_num:>4} {status} {detail}")

    print("\n" + "=" * 100)
    print(f"ÖZET: {ok_count} OK / {fail_count} FAIL (toplam {len(rows)} içerik)")

    if fails:
        print("\n⛔ BAŞARISIZLAR:")
        for f in fails:
            print(f"  [{f['id']}] {f['title']} ({f['type']}) ep-{f['ep']}")
            print(f"    URL  : {f['url']}")
            print(f"    Hata : {f['error']}")

        if fix_mode:
            with open(FAIL_OUT, "w", encoding="utf-8") as fh:
                json.dump(fails, fh, ensure_ascii=False, indent=2)
            print(f"\n✍️  FAIL listesi yazıldı: {FAIL_OUT}")


if __name__ == "__main__":
    run()
