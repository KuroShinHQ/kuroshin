"""
Gemma 3 4B-IT injection test — Iron Inquisitor tarzı simüle.
Mevcut 8082 portuna direkt request, 3 farklı soru.
"""
import urllib.request, json, time, re

URL = 'http://localhost:8082/v1/chat/completions'
SYSTEM = ("You are Kuroshin, a sharp AI assistant. "
          "Your lord is kuroshin_user. "
          "Always start your reply with '⚔️ Lordum,' and answer in Turkish. Be brief.")

TESTS = [
    ("greeting",  "günaydın"),
    ("math",      "2 artı 2 kaçtır?"),
    ("task",      "Bugün hava nasıl olacak?"),
]

PARAMS = {
    'stream': False,
    'max_tokens': 128,
    'temperature': 1.0,
    'top_p': 0.95,
    'top_k': 64,
    'min_p': 0.0,
}

PASS = 0
FAIL = 0
results = []

def strip_think(t):
    return re.sub(r'<think>.*?</think>', '', t, flags=re.DOTALL).strip()

for name, user_msg in TESTS:
    payload = dict(PARAMS)
    payload['model'] = 'local'
    payload['messages'] = [
        {'role': 'system', 'content': SYSTEM},
        {'role': 'user',   'content': user_msg}
    ]
    data = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=data,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        body = json.loads(resp.read().decode())
        raw  = strip_think(body['choices'][0]['message']['content'])
        elapsed = time.time() - t0
        starts_lordum = raw.strip().startswith('⚔️ Lordum')
        is_turkish    = any(c in raw for c in 'çşğıöüÇŞĞİÖÜ') or len([w for w in raw.split() if len(w) > 2]) > 2
        loops_name    = raw.lower().count('kuroshin') > 2 or raw.lower().count('küröshin') > 1
        no_regurgitate = SYSTEM[:30].lower() not in raw.lower()

        ok = starts_lordum and not loops_name and no_regurgitate
        status = '✅ PASS' if ok else '❌ FAIL'
        if ok: PASS += 1
        else:  FAIL += 1

        results.append({
            'name': name,
            'status': status,
            'elapsed': elapsed,
            'starts_lordum': starts_lordum,
            'loops': loops_name,
            'regurgitate': not no_regurgitate,
            'response': raw[:250]
        })
    except Exception as e:
        FAIL += 1
        results.append({'name': name, 'status': '❌ ERROR', 'error': str(e)})

print("\n" + "="*60)
print("QWEN3-1.7B INJECT TEST SONUÇLARI")
print("="*60)
for r in results:
    print(f"\n[{r['status']}] {r['name']}")
    if 'error' in r:
        print(f"  HATA: {r['error']}")
    else:
        print(f"  Süre:       {r.get('elapsed',0):.1f}s")
        print(f"  ⚔️ Lordum:  {r.get('starts_lordum','?')}")
        print(f"  Tekrar:     {r.get('loops','?')}")
        print(f"  Regurgitat: {r.get('regurgitate','?')}")
        print(f"  Yanıt:      {r.get('response','')}")
        print("-"*60)

print(f"\nSONUÇ: {PASS}/{PASS+FAIL} PASS")
print("="*60)
