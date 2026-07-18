import urllib.request, urllib.parse, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

url = "https://ragnarscans.com/manga/buyu-imparatoru/"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode("utf-8", errors="replace")

# Tum nonce benzeri degerler
for m in re.finditer(r'"([^"]*nonce[^""]*)"\s*:\s*"([^"]{8,})"', html, re.IGNORECASE):
    print(f"  {m.group(1)}: {m.group(2)}")

# wp-manga script var mi
for m in re.finditer(r"wp.manga[^}]{0,500}", html, re.IGNORECASE):
    print("WP-MANGA:", m.group(0)[:300])
    break

# Chapters JSON embeds
for m in re.finditer(r"chapter[^{]{0,20}\{[^}]{10,200}\}", html, re.IGNORECASE):
    print("CH-JSON:", m.group(0)[:200])
    break
