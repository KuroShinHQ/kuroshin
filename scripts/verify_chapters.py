import urllib.request

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

# Büyü İmparatoru - ragnarscans bolum-N formatı doğrulama
check_nums = [1, 50, 100, 200, 300, 400, 465]
for n in check_nums:
    url = f"https://ragnarscans.com/manga/buyu-imparatoru/bolum-{n}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        print(f"OK  {resp.status} bolum-{n}")
    except urllib.error.HTTPError as e:
        print(f"ERR {e.code} bolum-{n}")
    except Exception as ex:
        print(f"EXC bolum-{n}: {ex}")
