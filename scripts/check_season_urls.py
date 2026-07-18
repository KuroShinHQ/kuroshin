"""
tranimaci.com sezon URL pattern araştırması
Çok sezonlu anime örnekleri üzerinden pattern çıkar
"""
import urllib.request, re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

def get_episode_links(site_url):
    req = urllib.request.Request(site_url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        html = resp.read().decode("utf-8", errors="replace")
        # Episode linkleri bul
        links = re.findall(r'href="(https://www\.tranimaci\.com/video/[^"]+)"', html)
        links = list(dict.fromkeys(links))
        return links, html
    except Exception as ex:
        return [], str(ex)

# Test: Çok sezonlu animeler
TEST_CASES = [
    # (İsim, sezon-1 slug, sezon-2 slug veya None)
    ("KonoSuba",         "konosuba",        "konosuba-2"),
    ("Tate no Yuusha",   "tate-no-yuusha-no-nariagari", "tate-no-yuusha-no-nariagari-2"),
    ("Attack on Titan",  "attack-on-titan", "attack-on-titan-2"),
    ("DanMachi",         "danmachi",        "danmachi-2"),
    ("Overlord",         "overlord",        "overlord-2"),
]

for name, slug1, slug2 in TEST_CASES:
    print(f"\n=== {name} ===")
    for slug in [slug1, slug2]:
        if not slug:
            continue
        url = f"https://www.tranimaci.com/anime/{slug}/"
        links, html = get_episode_links(url)
        if links:
            # İlk ve son ep linkini göster
            print(f"  [{slug}] {len(links)} ep link")
            print(f"    İlk: {links[-1]}")
            print(f"    Son: {links[0]}")
        elif isinstance(html, str) and len(html) < 100:
            print(f"  [{slug}] HATA: {html}")
        else:
            # Sayfada başka format var mı?
            # Tüm /video/ linklerini dene
            all_video = re.findall(r'/video/[^"\'<\s]+', html if isinstance(html, str) else "")
            if all_video:
                print(f"  [{slug}] Video linkler: {all_video[:3]}")
            else:
                print(f"  [{slug}] 404 veya ep linki yok")
