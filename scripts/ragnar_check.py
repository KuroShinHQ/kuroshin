import urllib.request, urllib.parse, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

url = "https://ragnarscans.com/manga/buyu-imparatoru/"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode("utf-8", errors="replace")

# Nonce'lari ara
nonce1 = re.search(r'manga_chapters_nonce["\s:]+([a-f0-9]{10,})', html)
nonce2 = re.search(r'"nonce"\s*:\s*"([a-f0-9]{10,})"', html)
print("manga_chapters_nonce:", nonce1.group(1) if nonce1 else None)
print("nonce:", nonce2.group(1) if nonce2 else None)

# Nonce iceren satirlari goster
for line in html.split("\n"):
    if "nonce" in line.lower() and len(line) < 500:
        print("LINE:", line.strip()[:300])
