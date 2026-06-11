"""Budget hard drop debug"""
import sys; sys.path.insert(0, "scripts")
from kuroshin_market_master import _parse_sahibinden_listings

html = (
    '<table><tbody>'
    '<tr class="searchResultsItem" data-id="111">'
    '<td class="searchResultsTitle"><a class="classifiedTitle" href="/ilan/ucuz-111" title="Ucuz Bisiklet">Ucuz Bisiklet</a></td>'
    '<td class="searchResultsPriceValue">2.500 TL</td>'
    '</tr>'
    '<tr class="searchResultsItem" data-id="222">'
    '<td class="searchResultsTitle"><a class="classifiedTitle" href="/ilan/pahali-222" title="Pahali Trek">Pahali Trek</a></td>'
    '<td class="searchResultsPriceValue">5.000 TL</td>'
    '</tr>'
    '</tbody></table>'
)
result = _parse_sahibinden_listings(html, budget=3000, limit=10, log_fn=print)
print("Result:", result)
for r in result:
    print(" -", r.get("title"), r.get("price"), r.get("butce_asimi"))
