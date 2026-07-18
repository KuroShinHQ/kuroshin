import urllib.request

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

SITES = [
    "mangawow.org",
    "mangawow.com",
    "mangadenizi.com",
    "merlintoon.com",
    "ragnarscans.com",
    "hayalistic.com.tr",
]

SLUGS = [
    "nano-machine",
    "nano-machine-2",
    "nano-machine-3",
    "nano-makine",
    "nano-machine-manhwa",
    "nano-machine-season-2",
]

print("=== Nano Machine sitesi arama ===")
for site in SITES:
    for slug in SLUGS:
        url = f"https://{site}/manga/{slug}/"
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            print(f"OK  {resp.status} https://{site}/manga/{slug}/")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"ERR {e.code} https://{site}/manga/{slug}/")
        except Exception as ex:
            print(f"EXC https://{site}/manga/{slug}/: {ex}")
