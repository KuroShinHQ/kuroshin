#!/usr/bin/env python3
import urllib.request, json, time
prompt = "2+2 nedir? sadece sayi"
body = {"model": "", "messages": [{"role": "user", "content": prompt}], "max_tokens": 50, "temperature": 0.1}
req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=300) as rsp:
        msg = json.loads(rsp.read())["choices"][0]["message"]
        content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
    elapsed = time.time() - t0
    print(f"Yanit ({elapsed:.1f}s): {content[:300]}")
except Exception as e:
    print(f"HATA ({time.time()-t0:.1f}s): {e}")
