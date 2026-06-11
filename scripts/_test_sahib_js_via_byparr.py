"""
Sahibinden JS bundle analizi — Byparr üzerinden fetch, bundle'larda API endpoint ara.
"""
import re, time, httpx
import curl_cffi.requests as req

# 1. Byparr ile ana sayfayı çek
print("=== Byparr ile ana sayfa ===")
r = httpx.post(
    "http://localhost:8191/v1",
    json={"cmd": "request.get", "url": "https://www.sahibinden.com/", "maxTimeout": 60000},
    timeout=70,
)
data = r.json()
if data.get("status") != "ok":
    print("Byparr fail:", data.get("message"))
    exit(1)

html = data["solution"]["response"]
final_url = data["solution"].get("url", "")
print(f"Final URL: {final_url}")
print(f"HTML size: {len(html)} chars")

# JS URL'leri çıkar
js_urls = re.findall(r'src=["\']?(https://static\.sahibinden\.com[^"\'>\s]+\.js[^"\'>\s]*)["\']?', html)
js_urls += re.findall(r'src=["\']?(https://[^"\'>\s]+sahibinden[^"\'>\s]+\.js[^"\'>\s]*)["\']?', html)
# Relative JS
rel_js = re.findall(r'src=["\']?(/[^"\'>\s]+\.js(?:\?[^"\'>\s]*)?)["\']?', html)
for rj in rel_js:
    js_urls.append("https://www.sahibinden.com" + rj)

js_urls = list(set(js_urls))
print(f"JS URL sayisi: {len(js_urls)}")
for u in js_urls[:5]:
    print(f"  {u[:100]}")

# 2. Her bundle'ı direkt curl_cffi ile çek (statik, CF korumalı değil)
api_pattern = re.compile(r'["\`](/(?:api|classifieds|search|classified|ilan|listing|ads)[^"\`\s<>{},;]{3,100})["\`]')
all_endpoints = set()

s = req.Session(impersonate="chrome131")
print("\n=== JS BUNDLE TARAMA ===")
for js_url in js_urls[:20]:
    try:
        rj = s.get(js_url, timeout=10)
        if rj.status_code == 200 and len(rj.text) > 200:
            matches = api_pattern.findall(rj.text)
            new = set(matches) - all_endpoints
            if new:
                print(f"\n[{js_url[-70:]}]")
                for m in sorted(new)[:15]:
                    print(f"  {m}")
            all_endpoints |= set(matches)
        else:
            print(f"  SKIP {rj.status_code} {js_url[-60:]}")
        time.sleep(0.3)
    except Exception as e:
        print(f"  ERR {js_url[-50:]}: {str(e)[:50]}")

# 3. Ham HTML içinde de ara
print("\n=== HTML'DEN DIREKT API STRING ===")
html_endpoints = api_pattern.findall(html)
new_from_html = set(html_endpoints) - all_endpoints
if new_from_html:
    for e in sorted(new_from_html)[:30]:
        print(f"  {e}")

all_endpoints |= set(html_endpoints)
interesting = [e for e in sorted(all_endpoints) if any(k in e.lower() for k in ["/api/", "search", "classif", "listing", "ilan", "/ads"])]
print(f"\nToplam ilginç endpoint: {len(interesting)}")
for e in interesting[:40]:
    print(f"  {e}")
