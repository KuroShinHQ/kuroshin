#!/usr/bin/env python3
import urllib.request, json, time, sys
for i in range(300):
    time.sleep(2)
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3)
        data = json.loads(r.read())
        if data.get("status") == "ok":
            print(f"OK {i*2}s")
            sys.exit(0)
    except Exception as e:
        err = str(e)
        if "503" not in err and "refused" not in err:
            print(f"Hata: {err[:60]}")
    if i % 30 == 0:
        print(f"bekle... {i*2}s")
print("TIMEOUT")
sys.exit(1)
