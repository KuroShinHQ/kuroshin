"""
Anime URL sagligi - tranimeizle.co hostlarini calisan sitelerde bul
Hedef siteler: turkanime.co, anizm.net, tranimaci.com
"""
import urllib.request, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# Test: turkanime.co slug pattern
# Format: https://www.turkanime.co/video/{slug}-{N}-bolum
# veya: https://www.turkanime.co/anime/{slug}/

ANIME_TESTS = [
    {
        "title": "Dungeon Meshi",
        "slugs": {
            "turkanime.co": ["dungeon-meshi", "delicious-in-dungeon", "dungeon-meshi-dungeon-yemekleri"],
            "anizm.net": ["dungeon-meshi", "delicious-in-dungeon"],
            "tranimaci.com": ["dungeon-meshi", "delicious-in-dungeon"],
        }
    },
    {
        "title": "Faraway Paladin",
        "slugs": {
            "turkanime.co": ["saihate-no-paladin", "faraway-paladin", "the-faraway-paladin"],
            "anizm.net": ["saihate-no-paladin", "faraway-paladin"],
            "tranimaci.com": ["saihate-no-paladin", "faraway-paladin"],
        }
    },
    {
        "title": "Uncle from Another World",
        "slugs": {
            "turkanime.co": ["uncle-from-another-world", "isekai-ojisan"],
            "anizm.net": ["uncle-from-another-world", "isekai-ojisan"],
            "tranimaci.com": ["uncle-from-another-world", "isekai-ojisan"],
        }
    },
    {
        "title": "Baki's Path",
        "slugs": {
            "turkanime.co": ["bakis-path", "baki-hanma", "baki"],
            "anizm.net": ["bakis-path", "baki-hanma"],
            "tranimaci.com": ["bakis-path", "baki-hanma"],
        }
    },
]

def try_url(url, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as ex:
        return f"EXC:{ex}"

# Anime sayfasi var mi?
for anime in ANIME_TESTS:
    print(f"\n=== {anime['title']} ===")
    for site, slugs in anime["slugs"].items():
        for slug in slugs:
            # Anime ana sayfa
            url = f"https://www.{site}/anime/{slug}/"
            result = try_url(url)
            if result == 200:
                print(f"  ANIME  OK  {url}")
                # Bölüm 1 var mi?
                ep1_url = f"https://www.{site}/video/{slug}-1-bolum"
                ep1_result = try_url(ep1_url)
                print(f"  EP-1   {ep1_result}  {ep1_url}")
                break
            elif result not in (404,):
                print(f"  ANIME  {result}  {url}")
