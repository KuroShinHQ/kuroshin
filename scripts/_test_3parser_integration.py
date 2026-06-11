"""
3-parser entegrasyon testi — Trendyol JSON + Epey curl_cffi + HB curl_cffi
Kanıt: Her site için gerçek ürün sayısı ve örnek veriler
ML YOK, Playwright YOK
"""
import sys, time
sys.path.insert(0, '/mnt/c/Kuroshin/scripts')

try:
    import curl_cffi.requests as req
except ImportError:
    import requests as req

from kuroshin_market_master import (
    _parse_trendyol_json,
    _parse_epey_curlcffi,
    _parse_listings_from_html,
    SITE_FETCHER,
)

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
}

BUDGET = 7000.0
QUERY  = 'kondisyon bisikleti'

print('=' * 60)
print('3-PARSER ENTEGRASYON TESTİ')
print(f'Bütçe: {BUDGET} TL | Sorgu: {QUERY}')
print(f'SITE_FETCHER TY : {SITE_FETCHER.get("trendyol.com")}')
print(f'SITE_FETCHER HB : {SITE_FETCHER.get("hepsiburada.com")}')
print(f'SITE_FETCHER EP : {SITE_FETCHER.get("epey.com")}')
print('=' * 60)

results_summary = {}

# ─── TRENDYOL ────────────────────────────────────────────────────────────────
print('\n[1/3] TRENDYOL — JSON embedded parser')
t0 = time.time()
url_ty = f'https://www.trendyol.com/sr?q={QUERY.replace(" ", "+")}&pi=1'
r = req.get(url_ty, impersonate='chrome131', timeout=20, headers=H)
fetch_t = round(time.time()-t0, 2)

products_ty = _parse_trendyol_json(r.text, BUDGET, 10,
                                    log_fn=lambda m: print(f'  LOG: {m}'))
results_summary['trendyol'] = len(products_ty)
print(f'  Fetch: {r.status_code} | {len(r.text):,}c | {fetch_t}s')
print(f'  Ürün: {len(products_ty)}')
for p in products_ty[:3]:
    print(f'    • {p["title"][:55]} — {p["price"]:,.0f} TL ⭐{p["rating"]:.1f}({p["review_count"]})')

# ─── EPEY ─────────────────────────────────────────────────────────────────────
print('\n[2/3] EPEY — curl_cffi #fiyatlar parser')
t0 = time.time()
url_ep = f'https://www.epey.com/kondisyon-bisikleti/'
r = req.get(url_ep, impersonate='chrome131', timeout=20, headers=H)
fetch_t = round(time.time()-t0, 2)

products_ep = _parse_epey_curlcffi(r.text, BUDGET, 10,
                                    log_fn=lambda m: print(f'  LOG: {m}'))
results_summary['epey'] = len(products_ep)
print(f'  Fetch: {r.status_code} | {len(r.text):,}c | {fetch_t}s')
print(f'  Ürün: {len(products_ep)}')
for p in products_ep[:3]:
    print(f'    • {p["title"][:55]} — {p["price"]:,.0f} TL ({p["review_count"]} site)')

# ─── HEPSİBURADA ─────────────────────────────────────────────────────────────
print('\n[3/3] HEPSİBURADA — curl_cffi chrome131')
t0 = time.time()
url_hb = f'https://www.hepsiburada.com/ara?q={QUERY.replace(" ", "+")}'
r = req.get(url_hb, impersonate='chrome131', timeout=20, headers=H)
fetch_t = round(time.time()-t0, 2)

products_hb = _parse_listings_from_html(r.text, 'hepsiburada', BUDGET, limit=10,
                                         log_fn=lambda m: print(f'  LOG: {m}'))
results_summary['hepsiburada'] = len(products_hb)
print(f'  Fetch: {r.status_code} | {len(r.text):,}c | {fetch_t}s')
print(f'  Ürün: {len(products_hb)}')
for p in products_hb[:3]:
    print(f'    • {p["title"][:55]} — {p["price"]:,.0f} TL ⭐{p.get("rating",0):.1f}')

# ─── ÖZET ─────────────────────────────────────────────────────────────────────
print('\n' + '=' * 60)
print('ÖZET')
total = sum(results_summary.values())
for site, n in results_summary.items():
    status = '✅' if n >= 3 else '❌'
    print(f'  {status} {site}: {n} ürün')
print(f'  TOPLAM: {total} ürün — Playwright: 0 — ML: 0')

if all(n >= 3 for n in results_summary.values()):
    print('\n✅ TÜM PARSER\'LAR ÇALIŞIYOR — ENTEGRASYON BAŞARILI')
else:
    failed = [s for s,n in results_summary.items() if n < 3]
    print(f'\n❌ BAŞARISIZ: {failed}')
