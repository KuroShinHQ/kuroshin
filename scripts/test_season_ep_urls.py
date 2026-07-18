import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TESTS = [
    ("KonoSuba S3 ep1",   "https://www.tranimaci.com/video/konosuba-s3-1-bolum"),
    ("KonoSuba S3 ep2",   "https://www.tranimaci.com/video/konosuba-s3-2-bolum"),
    ("Tate S3 ep1",       "https://www.tranimaci.com/video/tate-no-yuusha-no-nariagari-s3-1-bolum"),
    ("Overlord ep1",      "https://www.tranimaci.com/video/overlord-1-bolum"),
    ("Overlord S2-a",     "https://www.tranimaci.com/video/overlord-2-1-bolum"),
    ("Overlord S2-b",     "https://www.tranimaci.com/video/overlord-s2-1-bolum"),
    ("Overlord S2-c",     "https://www.tranimaci.com/video/overlord-season-2-1-bolum"),
    ("AoT ep1",           "https://www.tranimaci.com/video/attack-on-titan-1-bolum"),
    ("AoT S2-a",          "https://www.tranimaci.com/video/attack-on-titan-2-1-bolum"),
    ("AoT S2-b",          "https://www.tranimaci.com/video/attack-on-titan-s2-1-bolum"),
    ("AoT S2-c",          "https://www.tranimaci.com/video/attack-on-titan-season-2-1-bolum"),
    ("AoT S2 slug?",      "https://www.tranimaci.com/video/shingeki-no-kyojin-2-1-bolum"),
    ("DanMachi ep1",      "https://www.tranimaci.com/video/danmachi-1-bolum"),
    ("DanMachi S2-a",     "https://www.tranimaci.com/video/danmachi-2-1-bolum"),
    ("DanMachi S2-b",     "https://www.tranimaci.com/video/danmachi-s2-1-bolum"),
]

for name, url in TESTS:
    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    try:
        resp = urllib.request.urlopen(req, timeout=8)
        print(f"OK  {resp.status}  {name:25} {url}")
    except urllib.error.HTTPError as e:
        print(f"ERR {e.code}  {name:25} {url}")
    except Exception as ex:
        print(f"EXC       {name:25} {ex}")
