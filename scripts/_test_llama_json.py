#!/usr/bin/env python3
"""Test llama-server JSON mode."""
import requests, json

r = requests.post(
    "http://127.0.0.1:8080/v1/chat/completions",
    json={
        "model": "local",
        "messages": [{"role": "user", "content": "Sadece JSON cevapla: {\"sayi\": 42}. Hicbir aciklama yazma."}],
        "max_tokens": 100,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    },
    timeout=60,
)
print("status:", r.status_code)
data = r.json()
content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
print("content:", content)
print("---try parse:")
try:
    parsed = json.loads(content)
    print("PASS parsed:", parsed)
except Exception as e:
    print("FAIL parse:", e)
