#!/usr/bin/env python3
import urllib.request, json, time

def query(prompt, max_tok=50, temp=0.1, timeout=300):
    body = {"model": "", "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tok, "temperature": temp}
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as rsp:
        msg = json.loads(rsp.read())["choices"][0]["message"]
    content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
    elapsed = time.time() - t0
    return content, elapsed

tests = [
    ("Basit: 2+2 nedir?", "2+2 nedir? sadece sayi", 50),
    ("Kisa mantik: 35 hayvan 100 bacak", "Bir ciftlikte tavuklar ve koyunlar var. Toplam 35 hayvan ve 100 bacak var. Kac tavuk, kac koyun?", 200),
    ("Kod: fibonacci", "Python'da fibonacci fonksiyonu yaz, ``` icinde.", 500),
    ("JSON: kullanici profili", "Sadece JSON. Bir kisi objesi: name, age, job. Ornek: {\"name\":\"Ali\",\"age\":30}", 300),
]

for label, prompt, max_tok in tests:
    print(f"\n{label}...")
    try:
        content, elapsed = query(prompt, max_tok=max_tok, timeout=600)
        print(f"  Sure: {elapsed:.1f}s")
        print(f"  Yanit: {content[:100]}")
    except Exception as e:
        print(f"  HATA: {type(e).__name__} after {time.time():.0f}s")
