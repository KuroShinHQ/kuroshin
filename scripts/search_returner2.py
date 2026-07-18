"""Daha genis A Returner's Magic site araması"""
import urllib.request, re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Yeni siteler + alternatif sluglar
CANDIDATES = [
    # ragnarscans alternatif sluglar
    ("ragnarscans.com", "manga", "sihirbazin-donusu"),
    ("ragnarscans.com", "manga", "geri-donen-sihirbaz"),
    ("ragnarscans.com", "manga", "a-returners-magic"),
    # Diger potansiyel TR siteler
    ("mangaoku.net", "manga", "a-returners-magic-should-be-special"),
    ("mangaoku.net", "manga", "a-returners-magic"),
    ("turkmangaoku.com", "manga", "a-returners-magic-should-be-special"),
    ("mangaruhu.com", "manga", "a-returners-magic-should-be-special"),
    ("mangaruhu.com", "manga", "a-returners-magic"),
    ("mangaruhu.net", "manga", "a-returners-magic-should-be-special"),
    ("mangaship.com", "manga", "a-returners-magic-should-be-special"),
    ("manhwahentai.me", "manhwa", "a-returners-magic-should-be-special"),
    ("manhwaclan.com", "manhwa", "a-returners-magic-should-be-special"),
    ("leagueofcomics.com", "comic", "a-returners-magic-should-be-special"),
    # Madara siteler kök ara
    ("mangadenizi.com", "manga", "a-returners-magic-should-be-special"),
    ("merlintoon.com", "manga", "a-returners-magic-should-be-special"),
    ("merlintoon.com", "manga", "sihirbazin-donusu"),
]

for site, path, slug in CANDIDATES:
    url = f"https://{site}/{path}/{slug}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=8)
        print(f"OK  {resp.status} {url}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"ERR {e.code} {url}")
    except Exception as ex:
        t = type(ex).__name__
        if "timeout" not in str(ex).lower():
            print(f"EXC {t}: {url}")
        # Timeout'ları gösterme (sessiz geç)
