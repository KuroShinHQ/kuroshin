"""ML-free test suite fixture debug"""
import sys; sys.path.insert(0, "scripts")
from kuroshin_market_master import _parse_trendyol_json, _parse_epey_curlcffi, _parse_sahibinden_listings

# Test 1: Trendyol JSON parse
html_ty = """<html><script>window.__PRODUCT_LIST_APP_INITIAL_STATE__ = {"products":[{"name":"Test Bisiklet","price":"1.499,99","ratingScore":4.5,"reviewCount":120,"variants":[{"images":[{"url":"/img/test.jpg"}]}],"url":"/test-bisiklet-p-123"},{"name":"Kondisyon Bisikleti X2","price":"2.899,00","ratingScore":4.2,"reviewCount":55,"variants":[{"images":[{"url":"/img/x2.jpg"}]}],"url":"/kondisyon-p-456"}]};</script></html>"""
try:
    r = _parse_trendyol_json(html_ty, budget=3000, limit=10)
    print("TY: {} urun, titles: {}".format(len(r), [x.get("title","?")[:30] for x in r]))
except Exception as e:
    print("TY FAIL:", e)

# Test 2: Epey link parse
html_epey = """<html><body><a href="/bisiklet/triathlon-t222#fiyatlar" title="Triathlon T-222 Kondisyon Bisikleti">Triathlon T-222 ></a><a href="/bisiklet/cosfer-r200#fiyatlar" title="Cosfer R200 Kondisyon Bisikleti">Cosfer R200 ></a></body></html>"""
try:
    r2 = _parse_epey_curlcffi(html_epey, budget=5000, limit=10)
    print("Epey: {} urun, titles: {}".format(len(r2), [x.get("title","?")[:30] for x in r2]))
except Exception as e:
    print("Epey FAIL:", e)

# Test 3: Sahibinden listing parse
html_sahib = """<table><tbody>
<tr class="searchResultsItem" id="item1">
  <td class="searchResultsTitle"><a href="/ilan/test-bisiklet-1234">Trek FX3 Bisiklet</a></td>
  <td class="searchResultsPriceValue"><span class="">2.500 TL</span></td>
  <td class="searchResultsCategory"><a>Bisiklet</a></td>
  <td class="searchResultsDateValue">11 Haz</td>
</tr>
<tr class="searchResultsItem" id="item2">
  <td class="searchResultsTitle"><a href="/ilan/kondisyon-5678">Triathlon Kondisyon</a></td>
  <td class="searchResultsPriceValue"><span class="">1.800 TL</span></td>
  <td class="searchResultsCategory"><a>Bisiklet</a></td>
  <td class="searchResultsDateValue">10 Haz</td>
</tr>
</tbody></table>"""
try:
    r3 = _parse_sahibinden_listings(html_sahib, budget=3000, limit=10)
    print("Sahib: {} ilan, titles: {}".format(len(r3), [x.get("title","?")[:30] for x in r3]))
except Exception as e:
    print("Sahib FAIL:", e)
