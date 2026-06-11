"""
HTML parser — JSON-LD (evrensel) + site-spesifik CSS selectors.
Kuroshin market_master parser'ından izole edilmiştir.

Desteklenen site tipleri:
  sahibinden  — tr.searchResultsItem[data-id]
  trendyol    — .product-card / .p-card-wrppr
  hepsiburada — li[class^="productListContent-"]
  epey        — a[href*="#fiyatlar"] + slug eşleştirme
  generic     — JSON-LD Product + genel başlık/fiyat selectors
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

# Çıktı dict anahtarları (tüm parser'lar aynı formatı döner)
# {"title": str, "price": float, "url": str, "site": str,
#  "description": str, "rating": float|None, "review_count": int}


def parse_listings(html: str, site_type: str = "generic",
                   site_label: str = "") -> List[Dict[str, Any]]:
    """
    HTML → ürün listesi.
    site_type: sahibinden | trendyol | hepsiburada | epey | generic
    site_label: çıktıda 'site' alanına yazılacak isim
    """
    if not html or not _HAS_BS4:
        if not _HAS_BS4:
            raise ImportError("beautifulsoup4 gerekli: pip install beautifulsoup4")
        return []

    label = site_label or site_type
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []

    parsers = {
        "sahibinden":  _parse_sahibinden,
        "trendyol":    _parse_trendyol,
        "hepsiburada": _parse_hepsiburada,
        "epey":        _parse_epey,
        "generic":     _parse_generic,
    }
    fn = parsers.get(site_type, _parse_generic)
    results = fn(soup, label)

    # Eksik alanları normalize et
    for item in results:
        item.setdefault("title", "")
        item.setdefault("price", 0.0)
        item.setdefault("url", "")
        item.setdefault("site", label)
        item.setdefault("description", "")
        item.setdefault("rating", None)
        item.setdefault("review_count", 0)

    return [r for r in results if r["title"] and r["price"] > 0]


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _price_from_text(text: str) -> float:
    """'15.500,00 TL' veya '15500 TL' → 15500.0"""
    text = text.replace("\xa0", " ").strip()
    m = re.search(r"([\d.]+)\s*,\s*(\d{2})\s*(?:TL|₺)", text)
    if m:
        try:
            return float(m.group(1).replace(".", "") + "." + m.group(2))
        except ValueError:
            pass
    m2 = re.search(r"([\d.]+)\s*(?:TL|₺)", text)
    if m2:
        try:
            return float(m2.group(1).replace(".", ""))
        except ValueError:
            pass
    # Sadece sayı (bazı siteler para birimi yok)
    m3 = re.search(r"([\d]{3,})", text.replace(".", "").replace(",", ""))
    if m3:
        try:
            return float(m3.group(1))
        except ValueError:
            pass
    return 0.0


def _ld_product(data: Any, site: str) -> Optional[Dict[str, Any]]:
    """JSON-LD Product dict → normalized listing dict."""
    if not isinstance(data, dict):
        return None
    t = data.get("@type", "")
    types = t if isinstance(t, list) else [t]
    if "Product" not in types:
        return None

    offers = data.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = 0.0
    if isinstance(offers, dict):
        raw = offers.get("price") or offers.get("lowPrice") or 0
        try:
            price = float(str(raw).replace(",", "."))
        except (ValueError, TypeError):
            pass

    rating = None
    review_count = 0
    ra = data.get("aggregateRating", {})
    if isinstance(ra, dict):
        try:
            rating = float(ra.get("ratingValue") or 0) or None
            review_count = int(float(ra.get("reviewCount") or ra.get("ratingCount") or 0))
        except (ValueError, TypeError):
            pass

    url = data.get("url", "")
    if isinstance(offers, dict):
        url = url or offers.get("url", "")

    return {
        "title": str(data.get("name", ""))[:200],
        "price": price,
        "url": str(url)[:500],
        "site": site,
        "description": str(data.get("description", ""))[:400],
        "rating": rating,
        "review_count": review_count,
    }


def _parse_jsonld(soup, site: str) -> List[Dict[str, Any]]:
    """Tüm JSON-LD Product'ları çıkar."""
    out = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string or script.get_text() or ""
            if not raw.strip():
                continue
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        # Tek Product
        item = _ld_product(data, site)
        if item:
            out.append(item)
            continue
        # ItemList
        if isinstance(data, dict):
            if data.get("@type") == "ItemList":
                for el in data.get("itemListElement", []):
                    sub = _ld_product(el.get("item") if isinstance(el, dict) else el, site)
                    if sub:
                        out.append(sub)
            if "@graph" in data:
                for el in data["@graph"]:
                    sub = _ld_product(el, site)
                    if sub:
                        out.append(sub)
        # Liste
        if isinstance(data, list):
            for el in data:
                sub = _ld_product(el, site)
                if sub:
                    out.append(sub)
    return out


# ---------------------------------------------------------------------------
# Site parsers
# ---------------------------------------------------------------------------

def _parse_sahibinden(soup, site: str) -> List[Dict[str, Any]]:
    """Sahibinden direkt listing — tr.searchResultsItem[data-id] row parser."""
    out = []
    rows = soup.select("tr.searchResultsItem[data-id]")
    for row in rows:
        try:
            ilan_id = row.get("data-id", "")
            a = row.select_one("a.classifiedTitle")
            if not a:
                continue
            title = (a.get_text(" ", strip=True) or a.get("title", ""))[:200]
            href = a.get("href", "")
            if href.startswith("/"):
                href = f"https://www.sahibinden.com{href}"

            price = 0.0
            price_el = row.select_one(".searchResultsPriceValue, [class*=price]")
            if price_el:
                price = _price_from_text(price_el.get_text(" ", strip=True))

            loc_el = row.select_one(".searchResultsLocationValue, [class*=location]")
            location = loc_el.get_text(" ", strip=True)[:60] if loc_el else ""

            desc_parts = []
            marka_el = row.select_one("[class*=searchResultsAttributeValue]")
            if marka_el:
                desc_parts.append(marka_el.get_text(" ", strip=True)[:50])
            if location:
                desc_parts.append(location)

            if not title or price <= 0:
                continue
            out.append({
                "title": title,
                "price": price,
                "url": href,
                "site": site,
                "description": " · ".join(desc_parts),
                "rating": None,
                "review_count": 0,
                "ilan_id": ilan_id,
            })
        except Exception:
            continue
    return out


def _parse_trendyol(soup, site: str) -> List[Dict[str, Any]]:
    """Trendyol — .product-card / .p-card-wrppr + JSON-LD fallback."""
    out = _parse_jsonld(soup, site)
    if out:
        return out
    cards = soup.select(".product-card, .p-card-wrppr")
    for card in cards:
        title_el = (card.select_one(".product-name") or
                    card.select_one(".prdct-desc-cntnr-name") or
                    card.select_one("[class*='product-down-text']"))
        price_el = (card.select_one("[class*='price-current']") or
                    card.select_one(".prc-box-dscntd") or
                    card.select_one("[class*='price-box']"))
        if not title_el or not price_el:
            continue
        title = title_el.get_text(" ", strip=True)[:200]
        price = _price_from_text(price_el.get_text(" ", strip=True))
        a = card.select_one("a[href]")
        href = a["href"] if a else ""
        if href.startswith("/"):
            href = f"https://www.trendyol.com{href}"
        if title and price > 0:
            out.append({"title": title, "price": price, "url": href, "site": site,
                        "description": "", "rating": None, "review_count": 0})
    return out


def _parse_hepsiburada(soup, site: str) -> List[Dict[str, Any]]:
    """Hepsiburada SSR — li[class^='productListContent-'] + JSON-LD fallback."""
    out = _parse_jsonld(soup, site)
    if out:
        return out
    cards = soup.select('li[class^="productListContent-"]')
    for card in cards:
        title_el = (card.select_one("h3") or card.select_one("h2") or
                    card.select_one("[data-test-id*='product-card-name']") or
                    card.select_one("a[title]"))
        price_el = (card.select_one('[class*="price"][class*="current"]') or
                    card.select_one('[data-test-id*="price"]') or
                    card.select_one('[class*="finalPrice"]'))
        if not title_el or not price_el:
            continue
        title = (title_el.get("title") or title_el.get_text(" ", strip=True))[:200]
        price = _price_from_text(price_el.get_text(" ", strip=True))
        a = card.select_one("a[href]")
        href = a["href"] if a else ""
        if href.startswith("/"):
            href = f"https://www.hepsiburada.com{href}"
        if title and price > 0:
            out.append({"title": title, "price": price, "url": href, "site": site,
                        "description": "", "rating": None, "review_count": 0})
    return out


def _parse_epey(soup, site: str) -> List[Dict[str, Any]]:
    """Epey — a[href*='#fiyatlar'] slug eşleştirme + JSON-LD fallback."""
    out = _parse_jsonld(soup, site)
    if out:
        return out
    for card in soup.select('a[href*="#fiyatlar"]'):
        href = card.get("href", "")
        if "#fiyatlar" not in href:
            continue
        slug = href.split("#")[0]
        if not slug or ".html" not in slug:
            continue
        price = _price_from_text(card.get_text(" ", strip=True))
        name_link = soup.find("a", href=lambda h: h and h.split("#")[0] == slug and "#" not in h)
        title = (name_link.get_text(" ", strip=True) if name_link else "")[:200]
        if not title:
            m = re.search(r"/([^/]+)\.html$", slug)
            title = m.group(1).replace("-", " ").title() if m else ""
        url = slug if slug.startswith("http") else f"https://www.epey.com{slug}"
        if title and price > 0:
            out.append({"title": title, "price": price, "url": url, "site": site,
                        "description": "", "rating": None, "review_count": 0})
    return out


def _parse_generic(soup, site: str) -> List[Dict[str, Any]]:
    """Genel parser — JSON-LD önce, sonra yaygın CSS pattern'lar."""
    out = _parse_jsonld(soup, site)
    if out:
        return out
    # Genel kartlar
    card_selectors = [
        "[class*='product-card']", "[class*='ProductCard']",
        "article[class*='product']", "[class*='item-card']",
        "li[class*='product']",
    ]
    cards = []
    for sel in card_selectors:
        cards = soup.select(sel)
        if cards:
            break
    for card in cards[:50]:
        title_el = (card.select_one("h3") or card.select_one("h2") or
                    card.select_one("[class*='title']") or card.select_one("[class*='name']"))
        price_el = (card.select_one("[class*='price']") or
                    card.select_one("[class*='Price']"))
        if not title_el or not price_el:
            continue
        title = title_el.get_text(" ", strip=True)[:200]
        price = _price_from_text(price_el.get_text(" ", strip=True))
        a = card.select_one("a[href]")
        href = a["href"] if a else ""
        if title and price > 0:
            out.append({"title": title, "price": price, "url": href, "site": site,
                        "description": "", "rating": None, "review_count": 0})
    return out
