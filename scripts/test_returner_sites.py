import urllib.request, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

SITES = [
    ("manhwahentai.me", "manhwa", "a-returners-magic-should-be-special"),
    ("leagueofcomics.com", "comic", "a-returners-magic-should-be-special"),
]

for site, path, slug in SITES:
    print(f"\n=== {site} ===")
    # Ana sayfa
    base_url = f"https://{site}/{path}/{slug}/"
    req = urllib.request.Request(base_url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        html = resp.read().decode("utf-8", errors="replace")
        # data-id bul
        did = re.search(r'data-id="(\d+)"', html)
        print(f"  Manga sayfa: 200 OK, data-id={did.group(1) if did else None}")
        # Chapter link'leri bul
        ch_links = re.findall(rf"https://{re.escape(site)}/[^\"']+chapter[^\"']+", html)
        ch_links = list(dict.fromkeys(ch_links))[:3]
        if ch_links:
            print(f"  Chapter linkler: {ch_links}")
    except Exception as ex:
        print(f"  Ana sayfa HATA: {ex}")

    # Bolum-1 formatları dene
    for fmt in ["chapter-1", "bolum-1", "chapter-1-0", "bolum-1-oku", "read/1"]:
        url = f"https://{site}/{path}/{slug}/{fmt}/"
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            print(f"  OK {resp.status} /{fmt}/")

            # Madara img test
            html2 = resp.read().decode("utf-8", errors="replace")
            imgs = re.findall(r'(?:data-src|src)=["\']([^"\']*\.(?:jpg|jpeg|png|webp|avif)[^"\']*)["\']', html2)
            _SKIP = ("logo", "favicon", "banner", "avatar", "themes", "elementor")
            imgs = [i for i in imgs if not any(s in i.lower() for s in _SKIP)]
            print(f"    img sayisi: {len(imgs)}")
            break
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"  ERR {e.code} /{fmt}/")
        except Exception as ex:
            pass
