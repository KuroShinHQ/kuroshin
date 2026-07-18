import urllib.request, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

for site in ["ragnarscans.com", "mangawow.org", "mangawow.com", "hayalistic.com.tr", "merlintoon.com"]:
    search_url = f"https://{site}/?s=returner"
    req = urllib.request.Request(search_url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="replace")
        links = re.findall(rf"https://{re.escape(site)}/manga/([^\"'/]+)", html)
        links = list(dict.fromkeys(links))[:5]
        if links:
            print(f"OK [{site}]: {links}")
        else:
            print(f"--- [{site}]: sonuc yok")
    except Exception as ex:
        print(f"ERR [{site}]: {ex}")
