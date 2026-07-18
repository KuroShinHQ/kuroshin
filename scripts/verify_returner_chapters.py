import urllib.request, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

BASE = "https://manhwahentai.me/manhwa/a-returners-magic-should-be-special"

# 1) ?style=list desteği var mi?
print("=== ?style=list test ===")
url = f"{BASE}/chapter-1/?style=list"
req = urllib.request.Request(url, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=12)
    html = resp.read().decode("utf-8", errors="replace")
    imgs = re.findall(r'(?:data-src|src)=["\']([^"\']*\.(?:jpg|jpeg|png|webp|avif)[^"\']*)["\']', html)
    _SKIP = ("logo", "favicon", "banner", "avatar", "themes", "elementor")
    imgs = [i for i in imgs if not any(s in i.lower() for s in _SKIP)]
    print(f"  ?style=list: 200 OK, {len(imgs)} img")
except Exception as ex:
    print(f"  ?style=list HATA: {ex}")

# 2) Önemli chapter'ları test et (1, 50, 100, 200, 268)
print("\n=== Chapter varlik testi ===")
for n in [1, 50, 100, 150, 200, 250, 268]:
    url = f"{BASE}/chapter-{n}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"  OK  {resp.status} chapter-{n}")
    except urllib.error.HTTPError as e:
        print(f"  ERR {e.code} chapter-{n}")
    except Exception as ex:
        print(f"  EXC chapter-{n}: {ex}")
