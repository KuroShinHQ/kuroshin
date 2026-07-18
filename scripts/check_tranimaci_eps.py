"""
tranimaci.com anime sayfasından episode listesi çıkar
Episode URL pattern'ini anlamak için
"""
import urllib.request, re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

def get_episodes(anime_url):
    req = urllib.request.Request(anime_url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        html = resp.read().decode("utf-8", errors="replace")
        # Episode linkleri - /video/ pattern
        links = re.findall(r'href="(https://www\.tranimaci\.com/video/[^"]+)"', html)
        links = list(dict.fromkeys(links))
        return links, html
    except Exception as ex:
        return [], str(ex)

TESTS = [
    ("KonoSuba S3",      "https://www.tranimaci.com/anime/konosuba-s3/"),
    ("Tate S3",          "https://www.tranimaci.com/anime/tate-no-yuusha-no-nariagari-s3/"),
    ("Overlord",         "https://www.tranimaci.com/anime/overlord/"),
    ("Dungeon Meshi",    "https://www.tranimaci.com/anime/dungeon-meshi/"),
    ("Attack on Titan",  "https://www.tranimaci.com/anime/attack-on-titan/"),
]

for name, url in TESTS:
    print(f"\n=== {name} ===")
    print(f"  URL: {url}")
    links, html = get_episodes(url)
    if links:
        print(f"  {len(links)} episode linki bulundu")
        print(f"  İlk: {links[-1]}")
        print(f"  Son: {links[0]}")
    else:
        # Sayfada ne var?
        # data-id, sezon bilgisi, js embed vs
        did = re.search(r'data-id="(\d+)"', html if isinstance(html, str) else "")
        ajax = re.search(r'ajax[^"]*url[^"]*"([^"]+)"', html if isinstance(html, str) else "")
        sezon_info = re.findall(r'sezon[^<]{0,50}', html.lower() if isinstance(html, str) else "")
        print(f"  Ep linki YOK - data-id={did.group(1) if did else None}")
        if sezon_info:
            print(f"  Sezon bilgisi: {sezon_info[:3]}")
        # Sayfa HTML'inde ne var - kısa özet
        if isinstance(html, str) and len(html) > 100:
            # Sezon/episode ile ilgili bölüm
            for kw in ['bolum', 'episode', 'sezon', 'season']:
                idx = html.lower().find(kw)
                if idx > 0:
                    print(f"  '{kw}' context: ...{html[max(0,idx-30):idx+80]}...")
                    break
        else:
            print(f"  HTML hatası: {html[:100]}")
