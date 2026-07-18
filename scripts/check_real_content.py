"""
tranimaci.com 200 döndürüyor ama gerçek video var mı?
Sayfa HTML'ini inceleyerek video player embed var mı bak.
"""
import urllib.request, re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

TESTS = [
    ("Overlord S1 ep1",   "https://www.tranimaci.com/video/overlord-1-bolum"),
    ("Overlord S2-a",     "https://www.tranimaci.com/video/overlord-2-1-bolum"),
    ("Overlord S2-b",     "https://www.tranimaci.com/video/overlord-s2-1-bolum"),
    ("AoT ep1",           "https://www.tranimaci.com/video/attack-on-titan-1-bolum"),
    ("AoT S2-a",          "https://www.tranimaci.com/video/attack-on-titan-2-1-bolum"),
    ("SAHTE URL",         "https://www.tranimaci.com/video/aaaa-bbbb-1-bolum"),  # Var olmayan URL
    ("Dungeon Meshi ep1", "https://www.tranimaci.com/video/dungeon-meshi-1-bolum"),
]

VIDEO_MARKERS = [
    r'iframe[^>]*src=["\'][^"\']*(?:youtube|dailymotion|youtu\.be|embed|player)[^"\']*["\']',
    r'source[^>]*src=["\'][^"\']*\.(?:mp4|m3u8|mkv)[^"\']*["\']',
    r'jwplayer|videojs|plyr|flowplayer',
    r'video-js|data-setup|mediaelement',
    r'<video[^>]+>',
    r'embed-player|izle-player|video-container',
]

for name, url in TESTS:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        html = resp.read().decode("utf-8", errors="replace")
        found = []
        for pat in VIDEO_MARKERS:
            if re.search(pat, html, re.IGNORECASE):
                found.append(pat[:30])
        # Sayfa başlığı
        title_m = re.search(r'<title>([^<]+)</title>', html)
        title = title_m.group(1).strip()[:60] if title_m else "?"
        has_video = "✅ VİDEO VAR" if found else "❌ video yok"
        print(f"{has_video} | {name:22} | {title}")
        if found:
            print(f"   Markers: {found[:2]}")
    except Exception as ex:
        print(f"ERR {name}: {ex}")
