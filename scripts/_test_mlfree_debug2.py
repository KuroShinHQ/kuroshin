"""ML-free fixture debug v2 — log_fn ile parser trace"""
import sys; sys.path.insert(0, "scripts")
from kuroshin_market_master import _parse_trendyol_json, _parse_epey_curlcffi, _parse_sahibinden_listings
from bs4 import BeautifulSoup

# --- Trendyol ---
html_ty = (
    '<html><script>window.__PRODUCT_LIST_APP_INITIAL_STATE__ = '
    '{"products":['
    '{"name":"Test Bisiklet","price":"1.499,99","ratingScore":4.5,"reviewCount":120,'
    '"variants":[{"images":[{"url":"/img/test.jpg"}]}],"url":"/test-bisiklet-p-123"},'
    '{"name":"Kondisyon X2","price":"2.899,00","ratingScore":4.2,"reviewCount":55,'
    '"variants":[{"images":[{"url":"/img/x2.jpg"}]}],"url":"/kondisyon-p-456"}'
    ']};</script></html>'
)
print("=== TRENDYOL ===")
r = _parse_trendyol_json(html_ty, budget=3000, limit=10, log_fn=print)
print("result:", r)

# --- Epey ---
html_epey = (
    "<html><body>"
    '<a href="/bisiklet/triathlon-t222#fiyatlar" title="Triathlon T-222 Kondisyon">Triathlon ></a>'
    '<a href="/bisiklet/cosfer-r200#fiyatlar" title="Cosfer R200 Kondisyon">Cosfer ></a>'
    "</body></html>"
)
print("\n=== EPEY ===")
r2 = _parse_epey_curlcffi(html_epey, budget=5000, limit=10, log_fn=print)
print("result:", r2)

# --- Sahibinden selector ---
html_s = (
    "<table><tbody>"
    '<tr class="searchResultsItem" id="item1">'
    '<td class="searchResultsTitle"><a href="/ilan/test-1234">Trek Bisiklet</a></td>'
    '<td class="searchResultsPriceValue"><span>2.500 TL</span></td>'
    '<td class="searchResultsCategory"><a>Bisiklet</a></td>'
    '<td class="searchResultsDateValue">11 Haz</td>'
    "</tr></tbody></table>"
)
print("\n=== SAHİBİNDEN selector debug ===")
soup = BeautifulSoup(html_s, "html.parser")
rows = soup.select("tr.searchResultsItem")
print("searchResultsItem rows:", len(rows))
if rows:
    print("Row0 html:", rows[0])

r3 = _parse_sahibinden_listings(html_s, budget=3000, limit=10, log_fn=print)
print("sahib result:", r3)
