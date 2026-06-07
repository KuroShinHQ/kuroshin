"""FAZ-A (mini pedal) + FAZ-C v2 (Gizli Hazine) izole test."""
import sys
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_market_master import _parse_listings_from_html, gizli_hazine_dedektoru

# --- FAZ-A: Mini Pedal Tespiti ---
html_mini = (
    "<html><body>"
    "<script type='application/ld+json'>"
    "["
    '{"@type":"Product","name":"Walke Mini El ve Ayak Egzersiz Bisikleti",'
    '"offers":{"price":"1599","priceCurrency":"TRY"},"url":"https://hepsiburada.com/walke"},'
    '{"@type":"Product","name":"Triathlon T-222 Dikey Kondisyon Bisikleti",'
    '"offers":{"price":"2798","priceCurrency":"TRY"},"url":"https://hepsiburada.com/triathlon"},'
    '{"@type":"Product","name":"Reidan El Ayak Pedal Mini Egzersiz Aleti",'
    '"offers":{"price":"850","priceCurrency":"TRY"},"url":"https://hepsiburada.com/reidan"},'
    '{"@type":"Product","name":"Cosfer Ritmo Dikey Kondisyon Bisikleti",'
    '"offers":{"price":"2544","priceCurrency":"TRY"},"url":"https://hepsiburada.com/cosfer"}'
    "]"
    "</script></body></html>"
)

parsed = _parse_listings_from_html(html_mini, "hepsiburada", 3000.0, limit=10)
print("=== FAZ-A Mini Pedal Test ===")
pass_count = 0
fail_count = 0
for p in parsed:
    mini = p.get("is_mini_pedal", False)
    title = p["title"]
    price = p["price"]
    beklenen_mini = "el ve ayak" in title.lower() or ("el ayak" in title.lower() and "dikey" not in title.lower())
    status = "OK" if mini == beklenen_mini else "FAIL"
    if status == "OK":
        pass_count += 1
    else:
        fail_count += 1
    tag = "MINI" if mini else "FULL"
    print(f"  [{status}][{tag}] {title[:60]} — {price}TL")

print(f"\nFAZ-A sonuç: PASS={pass_count} FAIL={fail_count}")

# --- FAZ-C v2: Gizli Hazine Dedektörü (kural tabanlı, LLM yok) ---
print()
print("=== FAZ-C Gizli Hazine Dedektörü Test ===")
cases = [
    ("Temiz sağlam kondisyon bisikleti az kullanıldı garantili tertemiz", 900.0, 2500.0, "gizli_hazine"),
    ("Arızalı bozuk parça eksik çalışmıyor kondisyon bisikleti", 500.0, 2500.0, "riskli"),
    ("Kondisyon bisikleti satılık", 800.0, 2500.0, "belirsiz"),
    ("Kutusunda sıfır gibi tertemiz elden teslim acil az kullanıldı bakımlı", 1100.0, 2500.0, "gizli_hazine"),
]
faz_c_pass = 0
faz_c_fail = 0
for desc, price, ref, beklenen in cases:
    r = gizli_hazine_dedektoru("Bisiklet", desc, price, ref)
    tier = r["tier"]
    skor = r["skor"]
    status = "OK" if tier == beklenen else "FAIL"
    if status == "OK":
        faz_c_pass += 1
    else:
        faz_c_fail += 1
    print(f"  [{status}][{tier.upper():<15}] skor={skor} beklenen={beklenen} — {desc[:50]}")

print(f"\nFAZ-C sonuç: PASS={faz_c_pass} FAIL={faz_c_fail}")
print()
toplam_pass = pass_count + faz_c_pass
toplam_fail = fail_count + faz_c_fail
print(f"TOPLAM: {toplam_pass}/{toplam_pass+toplam_fail} PASS")
