"""
Kuroshin Market Master v1.0 — DALGA-6 FAZ-1 (2 Haziran 2026)
==============================================================
Otonom alışveriş protokolü ana modülü. Lord direktifi:
  "Ben saatlerce manuel filtreleyip tek tek ilan incelemeyeyim, Kuroshin tüm
   ürünleri tarasın, analiz etsin, filtrelesin, en mükemmel ürünü sunsun."

Mimari (DALGA-6 prob sonuçlarıyla aligned):
  - 3 site DIRECT: Epey + Trendyol + Hepsiburada (curl_cffi chrome124 TLS impersonate)
  - 1 site INDIRECT: Sahibinden (Lord doktrini "login YOK" → Google snippet + cimri/akakce)
  - LLM judge: llama-server local (Huihui 35B A3B)
  - Output: Telegram 5-mesaj akışı + inline keyboard

Açık doktrin:
  - İz bırakmadan (UA rotate, cookie persist, sequential, 5-15s random delay)
  - $0 maliyet (paid scraping API YOK, lokal arsenal)
  - Public veri (login YOK, oturum YOK)
"""
from __future__ import annotations
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Lazy imports — boot etkisi sıfır (kullanıcı tetiklemeden yüklenmez)
try:
    from curl_cffi import requests as cc_requests
except ImportError:
    cc_requests = None
try:
    import cloudscraper
except ImportError:
    cloudscraper = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
try:
    from playwright_stealth import Stealth
except ImportError:
    Stealth = None

# Local llama-server endpoint (kuroshin standard)
LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"

# Persisted state
KB_CACHE_PATH = Path("/mnt/c/Kuroshin/memory/category_criteria.json")
KB_CACHE_TTL_HOURS = 24

# ============================================================================
# DALGA-6 Smart Routing Tablosu (3 Haz 2026 19:30 — Playwright kanıt revize)
# 4 hedef site: epey.com + trendyol.com + hepsiburada.com + sahibinden.com
# ============================================================================
# Kanit (Lord izlerken, gerçek URL'ler ile Playwright + curl_cffi):
#   trendyol.com     → curl_cffi 596K char AMA CSR (JSON-LD 0, data-test-id 0) → PARSER 0 urun
#                      Playwright Chromium JS-render → 5 GERCEK urun (Cosfer 2544 TL, vs.)
#   hepsiburada.com  → curl_cffi 3.8M, li[class^="productListContent-"] 36 SSR urun (Cosfer 3990 TL, vs.) ✅
#                      Playwright headless ZARARLI → Akamai "Güvenlik" 1.3K (TLS impersonate sart!)
#   epey.com         → curl_cffi 196K AMA body sadece navigation menusu (kategori CSR-after-load)
#                      Playwright → 213K + .listelegr 10 GERCEK urun (Voit V-Fit 7520 TL, vs.)
#   sahibinden.com   → LOGIN ZORUNLU 2026 → indirect (cimri/akakce/DDG snippet)
SITE_FETCHER: Dict[str, Tuple[str, str]] = {
    "epey.com":        ("playwright",    "chromium"),
    "trendyol.com":    ("playwright",    "chromium"),
    "hepsiburada.com": ("curl_cffi",     "chrome124"),  # impersonate=chrome124 — TLS/JA3 Akamai bypass (headless yakalanıyor, ironik)
    "sahibinden.com":  ("indirect",      "google_snippet"),
    "_fallback":       ("cloudscraper",  "chrome/windows/desktop"),
}

# Lord doktrini "iz bırakmadan" — request arası random.uniform(5, 15) saniye delay
RATE_LIMIT_MIN_SEC = 5    # min 5s (random.uniform(5, 15) min sınır)
RATE_LIMIT_MAX_SEC = 15

# Telegram 5-mesaj akışı: _market_msg_baslangic + _market_msg_canli_durum + _market_msg_ana_rapor + _market_render_ascii_chart + _market_msg_derin_analiz
# Inline keyboard callback'leri: market_yeniden_ara, market_mod_degistir, market_tablo, market_derin, market_tum_linkler

# ============================================================================
# MerchantScorer mod ağırlıkları (MD v3 tablosu — V/R/F → MASTER)
# ============================================================================
MOD_WEIGHTS: Dict[str, Dict[str, float]] = {
    "butce":      {"v": 0.5, "r": 0.3, "f": 0.2},  # Bütçe Odaklı
    "guven":      {"v": 0.2, "r": 0.5, "f": 0.3},  # Güven Odaklı
    "performans": {"v": 0.3, "r": 0.2, "f": 0.5},  # Performans Odaklı
    "dengeli":    {"v": 0.4, "r": 0.3, "f": 0.3},  # Dengeli (varsayılan)
}

# 2.el kondisyon katsayısı (V-Score için)
KONDISYON_KATSAYISI = {
    "sifir_kutulu":   0.85,
    "az_kullanildi":  0.70,
    "cizik":          0.55,
    "kirik":          0.30,
}

# Kusur risk matrisi (R-Score için, Lord doktrini 4 tip)
KUSUR_RISK = {
    "kozmetik":    {"kesinti": -1, "ornek": ["ufak çizik", "etiket izi", "boya atması"]},
    "kullanim":    {"kesinti": -3, "ornek": ["kablo ezilmiş", "ekran çiziği", "koltuk yıpranması"]},
    "fonksiyonel": {"kesinti": -5, "ornek": ["motor ses yapıyor", "direnç ayarı bozuk", "garanti dışı tamir"]},
    "yapisal":     {"kesinti": -7, "ornek": ["şase çatlağı", "devre kartı yanığı", "kırık"]},
}


# ============================================================================
# LISTING PARSER (3 Haz 2026 FIX-ALL): JSON-LD primary + CSS fallback
# Lord direktifi: "prob testlerinde veri alabiliyorduk, dogru formul olmali"
# JSON-LD universal — buyuk e-ticaret siteleri Product structured data ekliyor
# ============================================================================
def _is_product_ld(data) -> bool:
    if not isinstance(data, dict):
        return False
    t = data.get("@type", "")
    if isinstance(t, list):
        return any(tt == "Product" for tt in t)
    return t == "Product"


def _ld_to_listing_dict(data: dict, site: str) -> Optional[Dict[str, Any]]:
    """JSON-LD Product → ProductListing kwargs dict."""
    if not _is_product_ld(data):
        return None
    offers = data.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = 0.0
    try:
        raw_price = offers.get("price", 0) if isinstance(offers, dict) else 0
        if raw_price in (None, "", 0):
            raw_price = offers.get("lowPrice", 0) if isinstance(offers, dict) else 0
        price = float(str(raw_price).replace(",", "."))
    except (ValueError, TypeError):
        pass
    rating = None
    review_count = 0
    rating_obj = data.get("aggregateRating", {})
    if isinstance(rating_obj, dict):
        try:
            rating = float(rating_obj.get("ratingValue") or 0) or None
            review_count = int(float(rating_obj.get("reviewCount") or rating_obj.get("ratingCount") or 0))
        except (ValueError, TypeError):
            pass
    url = data.get("url", "") or ""
    if isinstance(offers, dict):
        url = url or offers.get("url", "")
    return {
        "title": str(data.get("name", ""))[:200],
        "price": price,
        "url": str(url)[:500],
        "site": site,
        "rating": rating,
        "review_count": review_count,
        "description": str(data.get("description", ""))[:600],
    }


def _parse_listings_from_html(html: str, site: str, budget: float,
                              limit: int = 10, log_fn=None) -> List[Dict[str, Any]]:
    """Universal listing parser. JSON-LD primary + site-specific CSS fallback.
    Returns: list of dict (ProductListing kwargs).
    """
    log = log_fn or (lambda m: None)
    out: List[Dict[str, Any]] = []
    if not html or BeautifulSoup is None:
        return out
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return out

    # 1. JSON-LD Product structured data (universal — sitelere bağımsız)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            txt = script.string or script.get_text() or ""
            if not txt.strip():
                continue
            data = json.loads(txt)
        except (json.JSONDecodeError, TypeError):
            continue
        # Tek Product
        ld = _ld_to_listing_dict(data, site)
        if ld:
            out.append(ld)
            continue
        # ItemList içinde Product'lar
        if isinstance(data, dict) and data.get("@type") == "ItemList":
            for elem in data.get("itemListElement", []):
                item = elem.get("item") if isinstance(elem, dict) else None
                ld = _ld_to_listing_dict(item, site)
                if ld:
                    out.append(ld)
        # Liste of dicts
        if isinstance(data, list):
            for item in data:
                ld = _ld_to_listing_dict(item, site)
                if ld:
                    out.append(ld)
        # @graph wrapper
        if isinstance(data, dict) and "@graph" in data:
            for item in data["@graph"]:
                ld = _ld_to_listing_dict(item, site)
                if ld:
                    out.append(ld)
    log(f"[PARSER {site}] JSON-LD'den {len(out)} urun")

    # 2. CSS selectors SITE-SPESIFIK (3 Haz 2026 19:30 — Lord canli kanit revize)
    # Generic selectors (.title, [class*='title']) Trendyol homepage widget'larini
    # yakaliyordu ("Flas Urun", "En Cok Satan 1. Urun" sahte sonuc) — site-spesifik pin'li.
    if len(out) < 3:
        cards = []
        title_selectors: List[str] = []
        price_selectors: List[str] = []
        if "trendyol" in site:
            # Trendyol arama sayfasi (?q=) layout: .product-card kart icinde .product-brand + .product-name
            # Trendyol kategori sayfasi: .p-card-wrppr + .prdct-desc-cntnr-name
            cards = soup.select(".product-card, .p-card-wrppr")[:limit*3]
            title_selectors = [".product-name", ".prdct-desc-cntnr-name",
                               "[class*='product-down-text']", "span[class*='ProductName']"]
            price_selectors = ["[class*='price-current']", "[class*='discounted']",
                               ".prc-box-dscntd", "[class*='price-box']",
                               "div[class*='price']", "[class*='Price__']"]
        elif "hepsiburada" in site:
            # HB SSR — li[class^="productListContent-..."] (hash uçucu, prefix pin)
            cards = soup.select('li[class^="productListContent-"]')[:limit*2]
            title_selectors = ['h3', 'h2', '[class*="title"][class*="product"]',
                               'a[title]', '[data-test-id*="product-card-name"]']
            price_selectors = ['[class*="price"][class*="current"]', '[data-test-id*="price"]',
                               '[class*="finalPrice"]', '[class*="Price__"]', 'div[class*="price"]']
        elif "epey" in site:
            # Epey kategori — urun adi linkleri (/<cat>/<slug>.html) + fiyat linkleri (#fiyatlar) AYRI
            # Strateji: tum #fiyatlar linklerini al → href slug'ini kullanarak isim link'i ile esle
            # Bu Epey'in standart layout'u (3 Haz 2026 canli debug ile teyit)
            cards = soup.select('a[href*="#fiyatlar"]')[:limit*4]
            title_selectors = []
            price_selectors = []
        elif "cimri" in site:
            cards = soup.select('[class*="product-card"], [class*="ProductCard"], article[class*="product"]')[:limit*2]
            title_selectors = ['h3', 'h2', '[class*="ProductTitle"]', '[class*="title"]']
            price_selectors = ['[class*="Price"]', '[class*="price"]']
        elif "akakce" in site or "sahibinden_indirect" in site:
            # Akakce/Sahibinden indirect (4 Haz canli debug — 32 urun teyit):
            # Her urun: <li>...<a class="iC"><span class="pn_v8">{name}</span></a>
            #            <span class="pt_v8">{price} TL +N FIYAT</span>...</li>
            # name+price prefix class — version uçucu (pn_v8/pn_v9), prefix sabit
            cards = soup.select('li:has(span[class^="pn_v"]), li:has(a.iC)')[:limit*3]
            title_selectors = ['span[class^="pn_v"]', '[class^="pn_v"]', 'a[class*="iC"]']
            price_selectors = ['span[class^="pt_v"]', '[class^="pt_v"]']

        for card in cards:
            try:
                title = ""
                price = 0.0
                url = ""
                # Epey ozel — card = #fiyatlar linki; isim ayri linkten slug ile eslestir
                if "epey" in site:
                    href = card.get("href", "") or ""
                    if "#fiyatlar" not in href:
                        continue
                    # slug = /<cat>/<urun>.html (URL anchor'i kirp)
                    slug = href.split("#")[0]
                    if not slug or ".html" not in slug:
                        continue
                    # Fiyat metni: "7.520,50 TL 6 site, 7 fiyat"
                    fiyat_metin = card.get_text(" ", strip=True)
                    pm = re.search(r"([\d.]+),(\d{2})\s*(?:TL|₺)", fiyat_metin)
                    if not pm:
                        # ondalik yok: "7520 TL" gibi
                        pm2 = re.search(r"([\d.]+)\s*(?:TL|₺)", fiyat_metin)
                        if pm2:
                            try:
                                price = float(pm2.group(1).replace(".", ""))
                            except ValueError:
                                pass
                    else:
                        try:
                            price = float(pm.group(1).replace(".", "") + "." + pm.group(2))
                        except ValueError:
                            pass
                    # Urun adi — soup'ta ayni slug href'i kullanan, metni dolu link
                    name_link = soup.find("a", href=lambda h: h and h.split("#")[0] == slug
                                          and "#" not in h)
                    if not name_link or not name_link.get_text(strip=True):
                        # Daha gevsek arama (kart bos olabilir)
                        name_link = soup.find("a", href=re.compile(re.escape(slug) + r"$"))
                    title = (name_link.get_text(" ", strip=True) if name_link else "")[:200]
                    if not title or len(title) < 3:
                        # Son care: slug'dan isim cikar
                        m_slug = re.search(r"/([^/]+)\.html$", slug)
                        if m_slug:
                            title = m_slug.group(1).replace("-", " ").title()
                        else:
                            continue
                    url = slug if slug.startswith("http") else f"https://www.epey.com{slug}"
                else:
                    # Title — site-spesifik selectors sirayla dene
                    title_el = None
                    for sel in title_selectors:
                        title_el = card.select_one(sel)
                        if title_el:
                            break
                    if not title_el:
                        # Son care: a[title]
                        title_el = card.select_one("a[title]")
                    if not title_el:
                        continue
                    title = title_el.get("title") or title_el.get_text(" ", strip=True)
                    title = (title or "").strip()
                    # Trendyol — brand kart icinde ayri elemandir, title basina ekle
                    if "trendyol" in site:
                        brand_el = card.select_one(".product-brand, [class*='ProductBrand']")
                        if brand_el:
                            brand_txt = brand_el.get_text(" ", strip=True)
                            if brand_txt and brand_txt.lower() not in title.lower():
                                title = f"{brand_txt} {title}"
                    title = title[:200]
                    if not title or len(title) < 8:
                        continue
                    # Yasak placeholder kelimeler — "Flaş Ürün", "En Çok Satan", widget baslıkları
                    placeholders = ["flaş ürün", "flas urun", "en çok satan", "en cok satan",
                                    "fırsat ürün", "firsat urun", "öne çıkan", "one cikan",
                                    "tümünü gör", "tumunu gor", "kampanya", "favorilerim"]
                    if any(p in title.lower() for p in placeholders) and len(title) < 30:
                        continue
                    # Price
                    price_el = None
                    for sel in price_selectors:
                        price_el = card.select_one(sel)
                        if price_el:
                            break
                    if price_el:
                        price_text = price_el.get_text(" ", strip=True)
                        # "3.990 TL", "2.544,89 TL", "5.990 ,00 TL" (akakce bosluklu)
                        # TR format: nokta binlik ayraç, virgül ondalık
                        pm = re.search(r"([\d.]+)\s*(?:,(\d{1,2}))?\s*(?:TL|₺)", price_text)
                        if pm:
                            try:
                                int_part = pm.group(1).replace(".", "")
                                dec_part = pm.group(2) or "0"
                                price = float(f"{int_part}.{dec_part}")
                            except ValueError:
                                pass
                    # URL — FAZ-A 4 Haz fix: site "trendyol" gibi kisa form gelirse .com ekle
                    # 6 Haz fix: Sahibinden indirect → akakce.com (parser akakce'den cekiyor,
                    # URL akakce slug'i — sahibinden.com ile birlestirince 404 NOT FOUND)
                    a_el = card.select_one("a[href]") if card.name != "a" else card
                    url = (a_el.get("href", "") if a_el else "") or ""
                    if url.startswith("/"):
                        if "sahibinden_indirect" in site or "akakce" in site:
                            _site_base = "akakce.com"  # gerçek akakce slug
                        else:
                            _site_base = site.replace('_indirect', '')
                            if "." not in _site_base:
                                _site_base = f"{_site_base}.com"
                        url = f"https://www.{_site_base}{url}"

                # Min fiyat sart — placeholder/widget genelde 0 veya cok kucuk
                if price <= 0:
                    continue
                # FAZ-C Yorum Zekası — rating + has_photo_review extract (HB+Trendyol)
                _rating = None
                _photo = False
                if "trendyol" in site:
                    # Trendyol .product-card icinde .average-rating veya .rating-stars
                    r_el = card.select_one(".average-rating, .ratings-summary [class*=value], [class*=rating-score]")
                    if r_el:
                        r_txt = r_el.get_text(" ", strip=True)
                        pm_r = re.search(r"(\d[\.,]\d)", r_txt)
                        if pm_r:
                            try:
                                _rating = float(pm_r.group(1).replace(",", "."))
                            except ValueError:
                                pass
                elif "hepsiburada" in site:
                    # HB li[productListContent-]: rate-module_rating__19oVu (hash uçucu)
                    r_el = card.select_one('[class^="rate-module_rating"]')
                    if r_el:
                        r_txt = r_el.get_text(" ", strip=True)
                        pm_r = re.search(r"(\d[\.,]\d)", r_txt)
                        if pm_r:
                            try:
                                _rating = float(pm_r.group(1).replace(",", "."))
                            except ValueError:
                                pass
                    # rate-module_photoReviewIcon sinyali
                    if card.select_one('[class^="rate-module_photoReviewIcon"]'):
                        _photo = True
                out.append({
                    "title": title, "price": price, "url": url, "site": site,
                    "rating": _rating, "review_count": 0, "description": "",
                    "has_photo_review": _photo,
                })
            except Exception:
                continue
        log(f"[PARSER {site}] CSS site-spesifik: toplam {len(out)} urun (ratingli: "
            f"{sum(1 for x in out if x.get('rating'))} · fotolu: {sum(1 for x in out if x.get('has_photo_review'))})")

    # 3. Filtre: makul fiyat araligi (3 Haz 2026 FIX: HB "3 TL" parse hatasi engellendi)
    # Min: budget*5% (50-150 TL altı sahte parse), Max: budget*2.5 (anormal yuksek)
    min_price = max(50.0, budget * 0.05)
    max_price = budget * 2.5
    filtered = [x for x in out if x.get("title") and min_price <= x.get("price", 0) <= max_price]
    log(f"[PARSER {site}] filtrelendi: {len(filtered)}/{len(out)} (min={min_price:.0f} max={max_price:.0f} TL)")
    # Tekil baslık (FAZ-A 4 Haz: normalize dedup — bosluk/case/noktalama temizle)
    seen = set()
    unique = []
    for x in filtered:
        # marka + ana kelime + ikinci kelime → daha sağlam imza
        title_norm = re.sub(r"[^\w\s]", " ", x["title"].lower())
        title_norm = re.sub(r"\s+", " ", title_norm).strip()
        # ilk 6 kelime — "Cosfer Spinning Bike Kondisyon Bisikleti Ve Kondisyon" → key
        words = title_norm.split()[:6]
        key = " ".join(words) if words else x["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(x)
    return unique[:limit]


# ============================================================================
# DATA CLASSES
# ============================================================================
@dataclass
class FetchResult:
    """MarketFetcher dönüş yapısı."""
    url: str
    status: int
    text: str = ""
    title: str = ""
    elapsed_s: float = 0.0
    tier: str = ""  # curl_cffi / cloudscraper / indirect
    blocked: bool = False
    error: str = ""


@dataclass
class ProductListing:
    """Tek bir ürün ilanı (3 siteden veya Sahibinden indirect).
    FAZ-C (4 Haz 2026): has_photo_review (HB) + yorum_kalitesi (LLM analiz)."""
    title: str
    price: float          # TL
    url: str              # HTTPS only
    site: str             # epey / trendyol / hepsiburada / sahibinden
    rating: Optional[float] = None
    review_count: int = 0
    description: str = ""
    features: Dict[str, str] = field(default_factory=dict)
    is_second_hand: bool = False
    kondisyon: str = "sifir_kutulu"
    # FAZ-C Yorum Zekası
    has_photo_review: bool = False  # HB rate-module_photoReviewIcon sinyali
    yorum_kalitesi: float = 0.0  # 0-10 LLM analiz (ileride)
    sikayet_pattern: List[str] = field(default_factory=list)  # LLM cikartma
    # FAZ-D Hazine Avi
    is_hazine: bool = False  # Sahibinden + epey_avg*0.6 alti + makul
    hazine_iskonto_pct: int = 0  # 0-99 (epey muadil ortalamasina gore)
    # Fix #4 (6 Haz): Cross-site dedup — aynı modelin alternatifleri
    alt_fiyat: float = 0.0  # en ucuz alternatif fiyat
    alt_site: str = ""  # en ucuz alternatif sitesi
    # FAZ-B (6 Haz): Sahibinden ilan detay LLM analiz
    aciklama_dolu: bool = False  # akakce/Sahibinden ilan aciklamasi dolu mu
    ilan_spec: Dict[str, str] = field(default_factory=dict)  # LLM cikartti
    eslesme_pct: int = 0  # Aydinlama kritikleri ile esleshme yuzdesi
    # FAZ-C (6 Haz): 4-seviye hazine kategori
    hazine_tier: str = ""  # 'onayli', 'supheli', 'potansiyel_elmas', 'normal'
    hazine_not: str = ""  # Lord doktrini metaforu ("camurda elmas" gibi)

    # Scores (MerchantScorer hesaplar)
    v_score: float = 0.0
    r_score: float = 0.0
    f_score: float = 0.0
    master_score: float = 0.0


# ============================================================================
# MarketFetcher — Smart routing + rate limit + UA rotate + cookie persist
# ============================================================================
class MarketFetcher:
    """4 hedef site için smart routing fetcher.

    Kullanım:
      mf = MarketFetcher()
      r = mf.fetch("https://www.epey.com/kondisyon-bisikleti/")
      if r.status == 200 and not r.blocked:
          # parse r.text
    """

    def __init__(self, log_fn=None):
        self.log = log_fn or (lambda msg: print(f"[MarketFetcher] {msg}"))
        self._last_request_ts: Dict[str, float] = {}
        # Lord doktrini: cookie persist (challenge çözümü için, login YOK)
        self._cookies: Dict[str, Any] = {}

    def _rate_limit_delay(self, domain: str):
        """Lord doktrini: iz bırakmadan — request başına 5-15s random delay."""
        last = self._last_request_ts.get(domain, 0)
        elapsed = time.time() - last
        delay = random.uniform(RATE_LIMIT_MIN_SEC, RATE_LIMIT_MAX_SEC)
        if elapsed < delay:
            sleep_for = delay - elapsed
            self.log(f"[RATE_LIMIT] domain={domain} sleep={sleep_for:.1f}s (iz bırakmama)")
            time.sleep(sleep_for)
        self._last_request_ts[domain] = time.time()

    def _domain_of(self, url: str) -> str:
        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        if not m:
            return "_fallback"
        host = m.group(1).lower()
        for known in SITE_FETCHER:
            if known != "_fallback" and known in host:
                return known
        return "_fallback"

    def _select_tier(self, domain: str) -> Tuple[str, str]:
        return SITE_FETCHER.get(domain, SITE_FETCHER["_fallback"])

    def _has_block_signature(self, text: str) -> bool:
        """CF/Akamai/DataDome interstitial signature detect."""
        if not text or len(text) < 500:
            return True
        t = text.lower()
        sigs = ["just a moment", "cf-ray", "cf_chl_", "checking your browser",
                "datadome", "incapsula", "akamai", "_cf_bm"]
        return any(s in t for s in sigs[:4])  # ilk 4 yeterli (last 4 olabilir ama içerikte legitimately)

    def _extract_title(self, html: str) -> str:
        if not html:
            return ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip()[:120] if m else ""

    def fetch(self, url: str, force_tier: Optional[str] = None) -> FetchResult:
        """Smart routing fetch. Domain'e göre tier seç, rate limit + UA rotate."""
        domain = self._domain_of(url)
        tier, profile = (force_tier, "chrome124") if force_tier else self._select_tier(domain)
        self._rate_limit_delay(domain)

        if tier == "indirect":
            # Sahibinden gibi login zorunlu siteler → indirect helper
            return self._fetch_indirect(url, domain)
        elif tier == "playwright":
            return self._fetch_playwright(url, domain)
        elif tier == "curl_cffi":
            return self._fetch_curlcffi(url, domain, profile)
        elif tier == "cloudscraper":
            return self._fetch_cloudscraper(url, domain)
        else:
            return FetchResult(url=url, status=0, error=f"Bilinmeyen tier: {tier}")

    def _fetch_playwright(self, url: str, domain: str) -> FetchResult:
        """3 Haz 2026 — JS-render sites (Trendyol kategori sayfasi CSR, Epey listelegr JS-load).
        Headless Chromium ile DOM tamamlanmasini bekle, page.content() dondur.
        Sync API kullanir (asyncio loop conflict yok)."""
        if sync_playwright is None:
            return FetchResult(url=url, status=0, tier="playwright",
                               error="playwright yuklu degil (pip install playwright + python -m playwright install chromium)")
        t0 = time.time()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-blink-features=AutomationControlled',
                          '--disable-features=IsolateOrigins,site-per-process'],
                )
                ctx = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                               '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    viewport={'width': 1366, 'height': 768},
                    locale='tr-TR',
                )
                page = ctx.new_page()
                # 6 Haz fix: playwright-stealth ile CF interstitial bypass
                # Bat 5+1 sonrasi yeni Chromium process'te CF cookie yok → challenge sayfa
                if Stealth is not None:
                    try:
                        Stealth().apply_stealth_sync(page)
                    except Exception:
                        pass
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                # CF challenge için ekstra 3s + DOM lazy-load
                page.wait_for_timeout(7000)
                # CF interstitial hala duruyorsa biraz daha bekle
                _t = page.title() or ""
                if "just a moment" in _t.lower() or "checking" in _t.lower():
                    page.wait_for_timeout(5000)
                html = page.content() or ""
                title = page.title() or ""
                browser.close()
            elapsed = round(time.time() - t0, 1)
            blocked = (len(html) < 2000) or self._has_block_signature(html)
            self.log(f"[PLAYWRIGHT] {domain} chars={len(html)} title={title[:50]!r} blocked={blocked} elapsed={elapsed}s")
            return FetchResult(
                url=url, status=200 if html else 0, text=html, title=title[:120],
                elapsed_s=elapsed, tier="playwright", blocked=blocked,
            )
        except Exception as e:
            return FetchResult(url=url, status=0, tier="playwright",
                               elapsed_s=round(time.time() - t0, 1),
                               error=f"{type(e).__name__}: {str(e)[:160]}")

    def _fetch_curlcffi(self, url: str, domain: str, impersonate_profile: str) -> FetchResult:
        if cc_requests is None:
            return FetchResult(url=url, status=0, error="curl_cffi yüklü değil (pip install curl_cffi)")
        t0 = time.time()
        try:
            r = cc_requests.get(url, impersonate=impersonate_profile, timeout=25)
            elapsed = round(time.time() - t0, 1)
            title = self._extract_title(r.text)
            blocked = (r.status_code != 200) or self._has_block_signature(r.text or "")
            if blocked and r.status_code == 200:
                self.log(f"[CURL_CFFI] {domain} 200 ama block-sig → cloudscraper fallback")
                return self._fetch_cloudscraper(url, domain)
            return FetchResult(
                url=url, status=r.status_code, text=r.text or "",
                title=title, elapsed_s=elapsed, tier="curl_cffi",
                blocked=blocked,
            )
        except Exception as e:
            return FetchResult(url=url, status=0, tier="curl_cffi",
                               elapsed_s=round(time.time() - t0, 1),
                               error=f"{type(e).__name__}: {str(e)[:120]}")

    def _fetch_cloudscraper(self, url: str, domain: str) -> FetchResult:
        if cloudscraper is None:
            return FetchResult(url=url, status=0, error="cloudscraper yüklü değil")
        t0 = time.time()
        try:
            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
            )
            r = scraper.get(url, timeout=25, allow_redirects=False)
            elapsed = round(time.time() - t0, 1)
            # 302 login redirect → blocked (Lord doktrini "login yok")
            if r.status_code in (301, 302):
                loc = r.headers.get("Location", "")[:120]
                if "login" in loc.lower() or "signin" in loc.lower():
                    self.log(f"[CLOUDSCRAPER] {domain} login redirect → BLOCKED")
                    return FetchResult(url=url, status=r.status_code, blocked=True,
                                       tier="cloudscraper", elapsed_s=elapsed,
                                       error=f"login redirect: {loc}")
            title = self._extract_title(r.text or "")
            blocked = (r.status_code != 200) or self._has_block_signature(r.text or "")
            return FetchResult(url=url, status=r.status_code, text=r.text or "",
                               title=title, elapsed_s=elapsed, tier="cloudscraper",
                               blocked=blocked)
        except Exception as e:
            return FetchResult(url=url, status=0, tier="cloudscraper",
                               elapsed_s=round(time.time() - t0, 1),
                               error=f"{type(e).__name__}: {str(e)[:120]}")

    def _fetch_indirect(self, url: str, domain: str) -> FetchResult:
        """Sahibinden gibi siteler için dolaylı veri (Google snippet + cimri/akakce)."""
        if "sahibinden.com" in domain:
            return self.fetch_sahibinden_indirect(url)
        return FetchResult(url=url, status=0, tier="indirect",
                           error=f"Indirect destek yok: {domain}")

    def fetch_sahibinden_indirect(self, ref_url_or_query: str) -> FetchResult:
        """FAZ-2 (2 Haz 2026): Sahibinden için dolaylı veri — login YOK doktrini.

        Strateji (önem sırasıyla):
          1. cimri.com agregator (curl_cffi chrome124) — Sahibinden fiyat snippet'leri
          2. akakce.com agregator (curl_cffi chrome124) — alternatif
          3. Google search snippet (web_search tool fallback)
          4. LLM ile snippet özet → ProductListing dönüştür (caller yapar)

        Lord doktrini: public veri, login YOK, iz bırakmadan (rate limit otomatik).
        """
        # Query string normalize (URL veya raw query)
        query = ref_url_or_query
        if "sahibinden.com" in query.lower():
            # URL'den anahtar kategori isim çıkar
            m = re.search(r"/([a-z0-9-]+)(?:/|\?|$)", query.lower())
            query = m.group(1).replace("-", " ") if m else "kondisyon bisikleti"
        self.log(f"[SAHIBINDEN_INDIRECT] query='{query[:60]}' — 4 katmanli dolayli")

        # 1. cimri.com — Türkiye'nin en büyük fiyat karşılaştırma agregatörü
        cimri_slug = query.lower().strip().replace(" ", "-")
        cimri_url = f"https://www.cimri.com/search?q={query.replace(' ', '+')}"
        r_cimri = self._fetch_curlcffi(cimri_url, "cimri.com", "chrome124")
        if r_cimri.status == 200 and not r_cimri.blocked and len(r_cimri.text) > 5000:
            self.log(f"[SAHIBINDEN_INDIRECT cimri] OK chars={len(r_cimri.text)}")
            r_cimri.tier = "indirect/cimri"
            return r_cimri

        # 2. akakce.com — alternatif agregator
        akakce_url = f"https://www.akakce.com/arama/?q={query.replace(' ', '+')}"
        r_akakce = self._fetch_curlcffi(akakce_url, "akakce.com", "chrome124")
        if r_akakce.status == 200 and not r_akakce.blocked and len(r_akakce.text) > 5000:
            self.log(f"[SAHIBINDEN_INDIRECT akakce] OK chars={len(r_akakce.text)}")
            r_akakce.tier = "indirect/akakce"
            return r_akakce

        # 3. Google search snippet — caller bu listeyi alıp LLM ile özetler
        snippet = self._google_search_snippet(f"site:sahibinden.com {query}")
        if snippet:
            self.log(f"[SAHIBINDEN_INDIRECT google_snippet] hits={len(snippet)} chars")
            return FetchResult(
                url=ref_url_or_query, status=200, text=snippet,
                tier="indirect/google_snippet", elapsed_s=0.0,
                title=f"Sahibinden dolaylı (google snippet): {query[:40]}",
            )

        # Hepsi fail
        return FetchResult(
            url=ref_url_or_query, status=0, tier="indirect",
            error=f"Sahibinden dolaylı 3 katman fail (cimri/akakce/google_snippet)",
        )

    def _google_search_snippet(self, query: str) -> str:
        """Google search snippet ile dolaylı veri (DuckDuckGo HTML fallback).

        Lord doktrini: web_search tool kullanımına alternatif. DDG HTML interface
        (https://duckduckgo.com/html/?q=...) — JavaScript-free, scrape-friendly.
        """
        ddg_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
        r = self._fetch_curlcffi(ddg_url, "duckduckgo.com", "chrome124")
        if r.status != 200 or r.blocked:
            return ""
        # DDG result snippet extract (BS4 varsa)
        if BeautifulSoup is None:
            return r.text[:3000]
        try:
            soup = BeautifulSoup(r.text, "html.parser")
            snippets = []
            for res in soup.select(".result__body, .web-result")[:15]:
                title_el = res.select_one(".result__title, h2")
                snippet_el = res.select_one(".result__snippet, .result__body")
                if title_el and snippet_el:
                    snippets.append(f"• {title_el.get_text(strip=True)[:120]}\n  {snippet_el.get_text(strip=True)[:200]}")
            return "\n".join(snippets)[:5000] if snippets else r.text[:3000]
        except Exception:
            return r.text[:3000]


# ============================================================================
# KnowledgeBase — Epey kategori kriter extractor (V/R/F'nin F-Score temeli)
# ============================================================================
# FIX-ALL C5: KnowledgeBase fallback statik kategori kriterleri (Epey BS4 0 dönerse)
CATEGORY_CRITERIA_DEFAULTS: Dict[str, List[str]] = {
    "kondisyon-bisikleti": ["volan", "direnç", "direnc", "tasima", "taşıma", "manyetik",
                            "sele", "gidon", "ekran", "monitor", "kalori", "kg"],
    "spinbike":           ["volan", "direnç", "ağırlık", "manyetik", "spin", "sele"],
    "klavye":             ["mekanik", "switch", "rgb", "kablosuz", "tepi", "anahtar", "türkçe"],
    "mekanik-klavye":     ["switch", "blue", "red", "brown", "rgb", "hotswap", "türkçe"],
    "telefon":            ["batarya", "ekran", "kamera", "ram", "5g", "depolama", "işlemci"],
    "akilli-telefon":     ["batarya", "amoled", "kamera", "ram", "5g", "depolama"],
    "laptop":             ["ram", "ssd", "ekran", "işlemci", "ekran kartı", "rtx", "batarya"],
    "kulaklik":           ["bluetooth", "anc", "anc", "pil", "kablosuz", "mikrofon"],
    "monitor":            ["hz", "ips", "inç", "ms", "qhd", "4k", "144"],
    "robot-supurge":      ["lidar", "mop", "emiş", "pa", "batarya", "harita"],
    # Generic fallback (en az kategori → bos string match)
    "_generic":           ["fiyat", "marka", "model", "yıl", "garanti"],
}


def _category_defaults(slug: str) -> List[str]:
    """Slug → static kritik listesi (Epey 0 kritik fallback)."""
    s = slug.lower()
    if s in CATEGORY_CRITERIA_DEFAULTS:
        return CATEGORY_CRITERIA_DEFAULTS[s]
    # Heuristic: en yakın match
    for known, kriters in CATEGORY_CRITERIA_DEFAULTS.items():
        if known != "_generic" and any(w in s for w in known.split("-")):
            return kriters
    return CATEGORY_CRITERIA_DEFAULTS["_generic"]


class KnowledgeBase:
    """Epey kategori sayfasından kritik özellikleri öğrenen modül.

    Örnek: kondisyon bisikleti kategori →
      {"volan_min_kg": 7, "direnc_min": 8, "tasima_min_kg": 120, "kritik": [...]}

    Cache: memory/category_criteria.json (TTL 24h).
    """

    def __init__(self, fetcher: MarketFetcher, log_fn=None):
        self.fetcher = fetcher
        self.log = log_fn or (lambda msg: print(f"[KnowledgeBase] {msg}"))
        self._cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if KB_CACHE_PATH.exists():
            try:
                return json.loads(KB_CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        KB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        KB_CACHE_PATH.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2),
                                 encoding="utf-8")

    def _cache_fresh(self, category: str) -> bool:
        entry = self._cache.get(category)
        if not entry:
            return False
        ts = entry.get("ts", 0)
        return (time.time() - ts) < KB_CACHE_TTL_HOURS * 3600

    def get_or_build(self, category_slug: str) -> Dict[str, Any]:
        """Kategori kriter sözlüğü dön (cache veya extract)."""
        if self._cache_fresh(category_slug):
            self.log(f"[KB cache HIT] {category_slug}")
            return self._cache[category_slug]
        self.log(f"[KB cache MISS] {category_slug} → Epey fetch")
        criteria = self._extract_from_epey(category_slug)
        self._cache[category_slug] = {
            "ts": time.time(),
            "criteria": criteria,
            "source": "epey",
        }
        self._save_cache()
        return self._cache[category_slug]

    def _extract_from_epey(self, category_slug: str) -> Dict[str, Any]:
        """Epey kategori sayfasından kritik özellikleri çıkar.
        FIX-ALL C5: Epey BS4 0 dönerse static fallback kategori defaults kullan."""
        url = f"https://www.epey.com/{category_slug}/"
        r = self.fetcher.fetch(url)
        criteria = {"kritik": [], "source_url": url}

        if r.status == 200 and r.text and BeautifulSoup is not None:
            try:
                soup = BeautifulSoup(r.text, "html.parser")
                # Epey filtre sidebar özellik adları — genişletilmiş selectors
                # Epey 2026 HTML: .filtre-grup .filtre-baslik, .opt h3, sidebar a
                selectors = [
                    ".filtre-baslik", ".ozellik-baslik", ".filtre-grup-baslik",
                    ".filter-title", "h3.title", "h4.title",
                    ".karsilastirma-baslik th", ".ozellikler th",
                    "aside h3", "aside h4", ".sidebar .baslik",
                ]
                for sel in selectors:
                    for tag in soup.select(sel)[:30]:
                        txt = tag.get_text(strip=True)
                        if 3 <= len(txt) <= 50 and not any(s in txt.lower() for s in
                                                          ["fiyat", "marka", "satıcı", "satici", "kategori"]):
                            if txt not in criteria["kritik"]:
                                criteria["kritik"].append(txt)
                self.log(f"[KB] Epey BS4: {len(criteria['kritik'])} kritik bulundu")
            except Exception as e:
                self.log(f"[KB] BS4 parse hata: {e}")
        elif r.status != 200:
            self.log(f"[KB] Epey fetch FAIL: {r.error or r.status}")

        # FIX-ALL C5: BS4'ten 0 veya az çıktıysa static fallback
        if len(criteria["kritik"]) < 3:
            fallback = _category_defaults(category_slug)
            self.log(f"[KB] Epey BS4 yetersiz, static fallback: {fallback[:5]}")
            criteria["kritik"] = fallback
            criteria["_fallback"] = "static_defaults"

        return criteria


# ============================================================================
# MerchantScorer — V/R/F → MASTER Score (4 mod ağırlık)
# ============================================================================
class MerchantScorer:
    """Ürün puanlama: Value/Risk/Feature → MASTER (mod bazlı ağırlık)."""

    def __init__(self, log_fn=None):
        self.log = log_fn or (lambda msg: print(f"[MerchantScorer] {msg}"))

    def calc_v_score(self, listing: ProductListing, ref_price: float,
                     is_second_hand: bool = False) -> float:
        """Value/Değer puanı 0-10."""
        if ref_price <= 0:
            return 5.0
        if is_second_hand:
            kondisyon_kat = KONDISYON_KATSAYISI.get(listing.kondisyon, 0.55)
            v = (ref_price * kondisyon_kat / max(listing.price, 1)) * 10
        else:
            delta_pct = (listing.price - ref_price) / ref_price
            v = 10 - (delta_pct * 10)
        return max(0.0, min(10.0, round(v, 2)))

    def calc_r_score(self, listing: ProductListing, platform_avg: float = 4.0,
                     min_anlamli_yorum: int = 50) -> float:
        """Risk/Güven puanı 0-10 (Bayesian + kusur matrisi)."""
        v_count = max(0, listing.review_count)
        R = listing.rating or 0.0
        C = platform_avg
        m = min_anlamli_yorum
        # Bayesian ağırlıklı satıcı puanı: (v / (v + m)) * R + (m / (v + m)) * C
        if v_count + m > 0:
            bayes = (v_count / (v_count + m)) * R + (m / (v_count + m)) * C
        else:
            bayes = C
        # 1-5 skalasından 0-10'a normalize
        r = (bayes / 5.0) * 10.0
        return max(0.0, min(10.0, round(r, 2)))

    def calc_f_score(self, listing: ProductListing, kritik_ozellikler: List[str]) -> float:
        """Feature/Özellik uygunluğu 0-10.
        Fix #5 (6 Haz): Sahibinden gibi başlığı kısa + açıklama yok ürünlerde
        f_score=0 haksızlık. 'Bilinmiyor' durumu = neutral 5.0 (Lord doktrini)."""
        if not kritik_ozellikler:
            return 5.0
        toplam = len(kritik_ozellikler)
        karsilanan = 0
        listing_features_str = " ".join(
            [str(v).lower() for v in listing.features.values()] +
            [listing.description.lower(), listing.title.lower()]
        ).strip()
        # Fix #5: corpus çok az ise (Sahibinden ilan: başlık+description birlikte <80 char)
        # bilgi YOK durumudur, sıfır demek haksız → neutral 5.0
        if len(listing_features_str) < 80:
            return 5.0
        for kriter in kritik_ozellikler:
            if kriter.lower() in listing_features_str:
                karsilanan += 1
        # Hiç kriter eşleşmediyse + corpus mevcut → yine de düşük puan (3.0 minimum)
        # Mevcut: 0 eşleşme → 0 (çok sert). Yeni: 0 eşleşme + corpus var → 3.0
        if karsilanan == 0:
            return 3.0
        return round((karsilanan / toplam) * 10.0, 2)

    def calc_master_score(self, listing: ProductListing, mod: str = "dengeli") -> float:
        """MASTER = (V * Wv) + (R * Wr) + (F * Wf)."""
        weights = MOD_WEIGHTS.get(mod, MOD_WEIGHTS["dengeli"])
        master = (listing.v_score * weights["v"] +
                  listing.r_score * weights["r"] +
                  listing.f_score * weights["f"])
        return round(master, 2)

    def score_all(self, listings: List[ProductListing], ref_price: float,
                  kritik_ozellikler: List[str], mod: str = "dengeli") -> List[ProductListing]:
        """Tüm ürünleri puanla + sırala.
        Fix #3 (6 Haz): Tie-break — master_score eşitse hazine_iskonto_pct DESC,
        sonra rating DESC, sonra price ASC. Lord doktrini: aynı puanda hazine üst."""
        for L in listings:
            L.v_score = self.calc_v_score(L, ref_price, L.is_second_hand)
            L.r_score = self.calc_r_score(L)
            L.f_score = self.calc_f_score(L, kritik_ozellikler)
            L.master_score = self.calc_master_score(L, mod)
        # Sort key: master DESC, hazine_iskonto DESC, rating DESC, price ASC
        return sorted(listings, key=lambda x: (
            -x.master_score,
            -x.hazine_iskonto_pct,
            -(x.rating or 0),
            x.price if x.price > 0 else 999999,
        ))


# ============================================================================
# FAZ-3 STUB'ları — LLM Reasoning (Tüccar Zekası)
# ============================================================================
def _safe_json_parse(raw: str) -> dict:
    """FAZ-3 (2 Haz 2026): Llama JSON yanit guvenli parse.
    Markdown code block strip + regex { ... } fallback (Llama bazen markdown sariyor)."""
    if not raw:
        return {}
    # 1. Markdown code block strip: ```json ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    # 2. Direkt parse dene
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # 3. Regex ile en buyuk { ... } blogu cikar
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _llm_json_call(prompt: str, llama_url: str, max_tokens: int = 600,
                   temperature: float = 0.0, timeout: int = 90) -> Tuple[dict, str]:
    """FAZ-3 LLM call wrapper — JSON mode + safe parse + raw response don.
    Returns: (parsed_dict, raw_response_text)
    """
    try:
        import requests
        r = requests.post(llama_url, json={
            "model": "local",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature,
            "response_format": {"type": "json_object"},
        }, timeout=timeout)
        raw = r.json()["choices"][0]["message"]["content"]
        return _safe_json_parse(raw), raw
    except Exception as e:
        return {}, f"EXC: {type(e).__name__}: {str(e)[:120]}"


def _web_arama_snippet(query: str, max_chars: int = 1500, log_fn=None) -> str:
    """FAZ-A (6 Haz 2026) — Aydinlama icin DDG web bilgi cek.
    Lord doktrini: 'LLM cevabi + web bilgisi ile zenginlestir, statik fallback zayif'.
    MarketFetcher._google_search_snippet'i bagimsiz cagri olarak yeniden kullan.
    """
    log = log_fn or (lambda m: None)
    try:
        fetcher = MarketFetcher(log_fn=log)
        snippet = fetcher._google_search_snippet(query)
        if snippet:
            return snippet[:max_chars]
    except Exception as e:
        log(f"[WEB_ARAMA] hata: {e}")
    return ""


def aydinlama_bulgusu(query: str, category_slug: str = "", budget: float = 0,
                      llama_url: str = LLAMA_URL, log_fn=None) -> Dict[str, Any]:
    """FAZ-B (4 Haz 2026) — Aydinlama Bulgusu: LLM kategoriden alici icin
    en kritik 3-5 ozelligi cikarir. Lord doktrini: 'model urunu tanimali'.
    FAZ-A revize (6 Haz 2026): LLM cevabina web_search bağlamı eklendi.

    Epey detay sayfa lazy-load + CF korumali → statik tabandi yerine LLM
    bilgisi kullan (35B Huihui yeterli kategori-bilgisi). Static fallback
    de var (CATEGORY_CRITERIA_DEFAULTS) — LLM fail olursa kullanir.

    Returns: {"kritik": ["volan_kg", "direnç_kademe", ...],
              "aciklama": "Bu kategoride alici icin...",
              "fiyat_aralik": "X-Y TL"}
    """
    if not query:
        query = category_slug.replace("-", " ") or "ürün"

    # FAZ-A (6 Haz): Web bağlamı çek — LLM cevabını zenginleştirmek için
    web_baglam = _web_arama_snippet(f"{query} özellikleri fiyat aralık 2026 Türkiye",
                                     max_chars=1200, log_fn=log_fn)
    web_kismi = f'\n\nGüncel web bilgisi (Türkiye, 2026):\n{web_baglam[:1000]}\n' if web_baglam else ""

    prompt = (
        f'Sen bir Türkiye e-ticaret danışmanısın. Alıcı şu ürünü arıyor: "{query}" '
        f'(bütçe: {budget:,.0f} TL).'
        + web_kismi +
        f'\n\nGÖREV: Bu kategoride alıcının BAKMASI GEREKEN en kritik 3-5 teknik '
        f'özelliği listele. Genel kelimeler değil, ÖLÇÜLEBİLİR özellikler '
        f'(örnek: "volan ağırlığı kg", "direnç kademe sayısı", "taşıma kapasitesi kg").\n'
        f'Eğer web bilgisi varsa GÜNCEL fiyat aralığını ve trend markaları dikkate al.\n\n'
        f'SADECE şu JSON yapısında yanıt ver (markdown YOK):\n'
        f'{{"kritik": ["ozellik_1", "ozellik_2", "ozellik_3", "ozellik_4", "ozellik_5"], '
        f'"aciklama": "1 cümle özet — neden bu özellikler önemli", '
        f'"fiyat_aralik": "X-Y TL beklenti", '
        f'"populer_markalar": ["marka1", "marka2", "marka3"]}}\n\n'
        f'JSON çıktı:'
    )
    data, raw = _llm_json_call(prompt, llama_url, max_tokens=500, temperature=0.1, timeout=60)
    if not data or not data.get("kritik"):
        # LLM fail → static fallback
        return {
            "kritik": _category_defaults(category_slug or _query_to_slug(query)),
            "aciklama": "(statik fallback — LLM cevap vermedi)",
            "fiyat_aralik": f"{budget*0.6:,.0f}-{budget*1.4:,.0f} TL",
            "populer_markalar": [],
            "web_baglam": bool(web_baglam),
            "raw_preview": raw[:120] if raw else "",
        }
    return {
        "kritik": data.get("kritik", [])[:5],
        "aciklama": data.get("aciklama", "")[:200],
        "fiyat_aralik": data.get("fiyat_aralik", "")[:60],
        "populer_markalar": data.get("populer_markalar", [])[:5],
        "web_baglam": bool(web_baglam),  # web bilgisi mi kullanildi
    }


# ============================================================================
# FAZ-D Lord Düşünce Profili (7 Haz 2026)
# Lord'un ürün alma karar süreci → Market Master'a yansır
# ============================================================================
LORD_PROFIL_PATH = Path("/mnt/c/Kuroshin/memory/lord_alisveris_profili.json")
_LORD_PROFIL_CACHE: Dict[str, Any] = {}


def _load_lord_profil() -> Dict[str, Any]:
    """Lord alışveriş profilini yükle (cached)."""
    global _LORD_PROFIL_CACHE
    if _LORD_PROFIL_CACHE:
        return _LORD_PROFIL_CACHE
    if not LORD_PROFIL_PATH.exists():
        return {}
    try:
        _LORD_PROFIL_CACHE = json.loads(LORD_PROFIL_PATH.read_text(encoding="utf-8"))
        return _LORD_PROFIL_CACHE
    except Exception:
        return {}


def _lord_skor_ayarla(listings: List["ProductListing"], log_fn=None) -> List["ProductListing"]:
    """FAZ-D: Lord profil tercihlerine göre listings master_score'larını ayarlar.
    Etki:
      - Site önceliği (Sahibinden +1.0, Epey +0.9, vb. çarpan)
      - Marka tercihi (tanıdık marka +0.5 / bilinmeyen -0.3)
      - Yorum bot eşiği (4-5 ⭐ ama yorum 0 = -2 ceza, foto var = +1.5)
    """
    log = log_fn or (lambda m: None)
    profil = _load_lord_profil()
    if not profil:
        return listings
    site_oncelik = profil.get("site_oncelik", {})
    yorum_esik = profil.get("yorum_bot_esik", {})
    marka_pref = profil.get("marka_tercih", {})
    tanidik = [m.lower() for m in marka_pref.get("tanidik_markalar", [])]
    tanidik_boost = float(marka_pref.get("tanidik_boost", 0.5))
    bilinmeyen_ceza = float(marka_pref.get("bilinmeyen_marka_ceza", -0.3))
    min_yildiz = float(yorum_esik.get("min_yildiz", 4.0))
    bot_ceza = float(yorum_esik.get("yildiz_yuksek_yorum_yok_ceza", -2.0))
    foto_bonus = float(yorum_esik.get("fotograf_bonus", 1.5))

    for L in listings:
        delta = 0.0
        notes = []
        # Site önceliği — çarpan
        oncelik = site_oncelik.get(L.site, 0.8)
        if oncelik != 1.0:
            old = L.master_score
            L.master_score = round(L.master_score * oncelik, 2)
            if oncelik > 1.0:
                notes.append(f"site×{oncelik}")
            elif oncelik < 0.9:
                notes.append(f"site×{oncelik}")
        # Marka tercihi
        title_lower = L.title.lower()
        marka_match = next((m for m in tanidik if m in title_lower), None)
        if marka_match:
            delta += tanidik_boost
            notes.append(f"marka+{tanidik_boost}")
        elif title_lower and len(title_lower) > 5:
            # Bilinmeyen marka — küçük ceza
            delta += bilinmeyen_ceza
        # Yorum bot ceza (rating var ama review_count YOK)
        if L.rating and L.rating >= min_yildiz and L.review_count == 0:
            delta += bot_ceza
            notes.append(f"botSupheli{bot_ceza}")
        # Foto bonus
        if L.has_photo_review:
            delta += foto_bonus
            notes.append(f"foto+{foto_bonus}")
        # Uygula (0-10 clip)
        if delta != 0:
            L.master_score = round(max(0.0, min(10.0, L.master_score + delta)), 2)
        if notes:
            L.hazine_not = (L.hazine_not + " · " if L.hazine_not else "") + " ".join(notes)
    log(f"[LORD_PROFIL] {len(listings)} listing skor ayarlandı")
    return listings


# ============================================================================
# Lord Cookie Aktarımı (6 Haz 2026) — Sahibinden direkt erişim
# Lord doktrini: "benim Sahibinden hesabım var" → cookie ile yetkili erişim
# ============================================================================
SAHIBINDEN_SESSION_PATH = Path("/mnt/c/Kuroshin/memory/sahibinden_session.json")

# Sahibinden kategori slug mapping — query term → çalışan slug (7 Haz 2026 test edildi)
# NOT: Her slug sahibinden.com/<slug> olarak test edildi. 404 alanlar EKLENMEDİ.
_SAHIB_SLUG_MAP: Dict[str, str] = {
    "telefon": "cep-telefonu-aksesuar",
    "cep telefon": "cep-telefonu-aksesuar",
    "akilli telefon": "cep-telefonu-aksesuar",
    "iphone": "cep-telefonu-aksesuar",
    "samsung telefon": "cep-telefonu-aksesuar",
    "kondisyon bisikleti": "kondisyon-bisikleti",
    "eliptik bisiklet": "kondisyon-bisikleti",
    "bisiklet": "bisiklet",
    "klavye": "klavye",
    # Diğer kategoriler (TV, tablet, laptop vb.) slug olarak çalışmıyor — direkt slug fallback dener
}


def _load_sahibinden_cookies() -> Dict[str, str]:
    """Lord cookies.txt veya CookieEditor export → dict[name, value].
    Format desteği:
      1. CookieEditor: [{"name":"X", "value":"Y", "domain":".sahibinden.com", ...}]
      2. Netscape cookies.txt: domain\tHTTP\tpath\tsecure\texpire\tname\tvalue
    """
    if not SAHIBINDEN_SESSION_PATH.exists():
        return {}
    try:
        txt = SAHIBINDEN_SESSION_PATH.read_text(encoding="utf-8").strip()
        # JSON formati (CookieEditor / Lord export)
        if txt.startswith("[") or txt.startswith("{"):
            data = json.loads(txt)
            if isinstance(data, dict):
                # Wrapper: {"cookies": [...]}
                data = data.get("cookies", [])
            if not isinstance(data, list):
                return {}
            out: Dict[str, str] = {}
            for c in data:
                if isinstance(c, dict):
                    name = c.get("name", "")
                    val = c.get("value", "")
                    domain = c.get("domain", "")
                    if name and val and ("sahibinden" in domain or not domain):
                        out[name] = val
            return out
        # Netscape format
        out2: Dict[str, str] = {}
        for line in txt.splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7 and "sahibinden" in parts[0]:
                out2[parts[5]] = parts[6]
        return out2
    except Exception:
        return {}


def _parse_sahibinden_listings(html: str, budget: float, limit: int = 20,
                                log_fn=None, query: str = "") -> List[Dict[str, Any]]:
    """Sahibinden direkt listing HTML parser (Lord cookies erişimi sonrası).
    Selector: tr.searchResultsItem[data-id] + a.classifiedTitle + searchResultsPriceValue
    """
    log = log_fn or (lambda m: None)
    out: List[Dict[str, Any]] = []
    if not html or BeautifulSoup is None:
        return out
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return out
    rows = soup.select("tr.searchResultsItem[data-id]")
    log(f"[SAHIBINDEN_PARSE] searchResultsItem: {len(rows)} row")
    # Çok sayfa veri: tüm satırları tara (PRICE_ASC ile ucuzlar önce gelir)
    for row in rows:
        try:
            ilan_id = row.get("data-id", "")
            if not ilan_id:
                continue
            # Başlık + URL
            a = row.select_one("a.classifiedTitle")
            if not a:
                continue
            title = (a.get_text(" ", strip=True) or a.get("title", ""))[:200]
            href = a.get("href", "")
            if href.startswith("/"):
                href = f"https://www.sahibinden.com{href}"
            # Fiyat
            price = 0.0
            price_el = row.select_one(".searchResultsPriceValue, td.searchResultsPriceValue div, [class*=price]")
            if price_el:
                ptxt = price_el.get_text(" ", strip=True)
                pm = re.search(r"([\d.]+)\s*(?:,(\d{2}))?\s*TL", ptxt.replace("\xa0", " "))
                if pm:
                    try:
                        int_part = pm.group(1).replace(".", "")
                        dec_part = pm.group(2) or "0"
                        price = float(f"{int_part}.{dec_part}")
                    except ValueError:
                        pass
            # Konum
            loc_el = row.select_one(".searchResultsLocationValue, [class*=location]")
            location = loc_el.get_text(" ", strip=True)[:60] if loc_el else ""
            # Açıklama özet — Sahibinden listing'de başlık altında bazen kısa açıklama
            desc = ""
            for cls in ["searchResultsTagAttributeValue", "shortDescription"]:
                d = row.select_one(f"[class*={cls}]")
                if d:
                    desc = d.get_text(" ", strip=True)[:300]
                    break
            if not title or price <= 0:
                continue
            # Aksesuar/kılıf filtresi — sadece telefon aramasında aktif
            # Bisiklet/diğer kategorilerde tüm ilanlar kabul edilir
            q_lower = query.lower()
            if href and "/ilan/" in href and ("telefon" in q_lower or "cep" in q_lower):
                is_telefon_ilan = any(x in href for x in [
                    "-cep-telefonu-aksesuar-cep-telefonu-",
                ])
                is_yepy = "/yepy/yenilenmis-telefonlar/" in href
                if not (is_telefon_ilan or is_yepy):
                    log(f"[SAHIBINDEN_PARSE] telefon-aksesuar/diğer atlandı: {title[:35]}")
                    continue
            out.append({
                "title": title,
                "price": price,
                "url": href,
                "site": "sahibinden",
                "rating": None,
                "review_count": 0,
                "description": desc + (f" · {location}" if location else ""),
                "has_photo_review": False,
                # Sahibinden = 2.el
                "is_second_hand": True,
                "kondisyon": "az_kullanildi",  # default tahmin
                # Sahibinden ilan ID
                "ilan_spec": {"sahibinden_id": ilan_id, "konum": location},
            })
        except Exception:
            continue
    log(f"[SAHIBINDEN_PARSE] toplam {len(out)} ilan extract edildi")
    # Filtre: fiyat budget*3 üst sınır (Lord doktrini bot/anomali)
    filtered = [x for x in out if 50 <= x["price"] <= budget * 3]
    return filtered[:limit]


def fetch_sahibinden_direct(query: str, log_fn=None) -> Optional["FetchResult"]:
    """Lord cookies ile Sahibinden kategori listesi direkt fetch.
    Returns: FetchResult veya None (cookies yoksa)."""
    log = log_fn or (lambda m: None)
    cookies = _load_sahibinden_cookies()
    if not cookies:
        log("[SAHIBINDEN_DIRECT] cookies YOK — akakce fallback'e geç")
        return None
    if cc_requests is None:
        log("[SAHIBINDEN_DIRECT] curl_cffi YOK")
        return None
    # Sahibinden URL stratejisi: 1) slug mapping 2) query slug 3) arama URL
    # 7 Haz fix: genel sorgular (telefon→cep-telefonu) için mapping kullan
    q_norm = query.lower().replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ğ", "g").replace("ü", "u").replace("ö", "o")
    q_norm = re.sub(r"\s+", " ", q_norm).strip()
    # Mapping'den bak (exact veya query'nin ilk kelimesi)
    mapped_slug = _SAHIB_SLUG_MAP.get(q_norm) or _SAHIB_SLUG_MAP.get(q_norm.split()[0] if q_norm.split() else "")
    direct_slug = q_norm.replace(" ", "-")
    direct_slug = re.sub(r"[^a-z0-9-]", "", direct_slug)
    # URL sıralaması: mapping varsa önce, sonra direct slug, sonra boş (arama sayfası JS-render gerektirir)
    candidate_slugs = []
    if mapped_slug and mapped_slug != direct_slug:
        candidate_slugs.append(mapped_slug)
    candidate_slugs.append(direct_slug)
    t0 = time.time()
    url = f"https://www.sahibinden.com/{candidate_slugs[0]}"
    r = None
    try:
        # Slug bul
        for slug_try in candidate_slugs:
            url = f"https://www.sahibinden.com/{slug_try}"
            r = cc_requests.get(url, impersonate="chrome124", cookies=cookies,
                                timeout=25, allow_redirects=False)
            if r.status_code == 200:
                break
            log(f"[SAHIBINDEN_DIRECT] /{slug_try} → {r.status_code}, sonraki dene")
        # Redirect kontrol: 2FA challenge vs login vs normal redirect
        if r and r.status_code in (301, 302):
            elapsed = round(time.time() - t0, 1)
            loc = r.headers.get("Location", "")
            if "iki-asamali" in loc or "CHLG" in loc:
                err_tag = "2fa_challenge"
                log(f"[SAHIBINDEN_DIRECT] 2FA challenge → {loc[:80]}")
            elif "login" in loc or "giris" in loc:
                err_tag = "login_redirect"
                log(f"[SAHIBINDEN_DIRECT] login redirect → {loc[:80]} (cookies expired)")
            else:
                err_tag = f"redirect:{loc[:80]}"
                log(f"[SAHIBINDEN_DIRECT] redirect → {loc[:80]}")
            return FetchResult(url=url, status=r.status_code, blocked=True,
                               tier="sahibinden_cookie", elapsed_s=elapsed,
                               error=err_tag)
        if not r or r.status_code != 200:
            elapsed = round(time.time() - t0, 1)
            return FetchResult(url=url, status=(r.status_code if r else 0),
                               tier="sahibinden_cookie", elapsed_s=elapsed,
                               blocked=True, error="no_200")
        # Eğer "Sonuç Bulunamadı" gelirse başarısız say
        if "Sonuç Bulunamadı" in (r.text or "")[:5000]:
            log(f"[SAHIBINDEN_DIRECT] 'Sonuç Bulunamadı' → başarısız")
            elapsed = round(time.time() - t0, 1)
            return FetchResult(url=url, status=200, tier="sahibinden_cookie",
                               elapsed_s=elapsed, blocked=True, error="sonuc_bulunamadi")
        # Tüm sayfaları tara — timeout bazlı (Lord: "gerekirse timeout at ama tüm sayfalar")
        base_slug = url.split("sahibinden.com/")[-1].split("?")[0]
        # Sayfa 1: PRICE_ASC sıralı
        price_sort_url = f"https://www.sahibinden.com/{base_slug}?sorting=PRICE_ASC"
        combined_html = ""
        try:
            r0 = cc_requests.get(price_sort_url, impersonate="chrome124", cookies=cookies,
                                  timeout=20, allow_redirects=False)
            if r0.status_code == 200 and r0.text:
                combined_html = r0.text
                log(f"[SAHIBINDEN_DIRECT] sayfa-1 (PRICE_ASC) {len(r0.text)} char")
        except Exception:
            pass
        if not combined_html:
            combined_html = r.text or ""
        # Sayfa 2+ timeout döngüsü — tüm ilan sayfaları
        page_deadline = t0 + 90  # 90s max pagination bütçesi
        page_offset = 20
        pages_fetched = 1
        while time.time() < page_deadline:
            try:
                page_url = f"https://www.sahibinden.com/{base_slug}?sorting=PRICE_ASC&pagingOffset={page_offset}"
                rp = cc_requests.get(page_url, impersonate="chrome124", cookies=cookies,
                                     timeout=20, allow_redirects=False)
                if rp.status_code != 200 or not rp.text:
                    log(f"[SAHIBINDEN_DIRECT] offset={page_offset} → {rp.status_code if rp else 'err'} DUR")
                    break
                if "searchResultsItem" not in rp.text:
                    log(f"[SAHIBINDEN_DIRECT] offset={page_offset} → ilan yok, son sayfa")
                    break
                combined_html += rp.text
                pages_fetched += 1
                log(f"[SAHIBINDEN_DIRECT] sayfa-{pages_fetched} offset={page_offset} +{len(rp.text)} char")
                page_offset += 20
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                log(f"[SAHIBINDEN_DIRECT] offset={page_offset} hata: {e}")
                break
        elapsed = round(time.time() - t0, 1)
        log(f"[SAHIBINDEN_DIRECT] {pages_fetched} sayfa birleşik chars={len(combined_html)} elapsed={elapsed}s")
        return FetchResult(
            url=url, status=200, text=combined_html,
            elapsed_s=elapsed, tier="sahibinden_cookie",
            blocked=False,
        )
    except Exception as e:
        return FetchResult(url=url, status=0, tier="sahibinden_cookie",
                           elapsed_s=round(time.time() - t0, 1),
                           error=f"{type(e).__name__}: {str(e)[:120]}")


def sahibinden_ilan_analiz(url: str, kritik_ozellikler: List[str],
                            llama_url: str = LLAMA_URL,
                            log_fn=None) -> Dict[str, Any]:
    """FAZ-B (6 Haz 2026) — Sahibinden/akakce ilan detay LLM analiz.
    Lord doktrini: 'EN KRİTİK: ilan AÇIKLAMASI'.

    1. URL'den detay sayfa fetch (curl_cffi)
    2. Açıklama metnini çıkar
    3. LLM özet: Aydınlama kritikleri ile eşleşme + spec dict

    Returns: {
        "aciklama_dolu": bool (>50 char teknik içerik),
        "aciklama_metin": str (max 600 char önizleme),
        "ilan_spec": {"model": "...", "volan_kg": "...", ...},
        "eslesme_pct": int (0-100, kritik kaçı geçti),
    }
    """
    log = log_fn or (lambda m: None)
    if not url or "http" not in url:
        return {"aciklama_dolu": False, "aciklama_metin": "", "ilan_spec": {}, "eslesme_pct": 0}
    # 1. Fetch — akakce/sahibinden için curl_cffi chrome124
    if cc_requests is None:
        return {"aciklama_dolu": False, "aciklama_metin": "", "ilan_spec": {}, "eslesme_pct": 0,
                "hata": "curl_cffi YOK"}
    try:
        r = cc_requests.get(url, impersonate="chrome124", timeout=20)
        if r.status_code != 200 or not r.text:
            return {"aciklama_dolu": False, "aciklama_metin": "", "ilan_spec": {}, "eslesme_pct": 0,
                    "hata": f"status {r.status_code}"}
    except Exception as e:
        return {"aciklama_dolu": False, "aciklama_metin": "", "ilan_spec": {}, "eslesme_pct": 0,
                "hata": f"fetch: {type(e).__name__}"}
    # 2. Açıklama çıkar (akakce + Sahibinden farklı yapılar)
    aciklama = ""
    if BeautifulSoup:
        try:
            soup = BeautifulSoup(r.text, "html.parser")
            # akakce ürün detay: itemprop=description veya .product-description
            for sel in ['[itemprop=description]', '.product-description', '.urun-bilgi',
                        '#urunbilgi', '.product-info', '[class*=description]', '.aciklama',
                        'div.classifiedDescription', '#classifiedDescription']:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(" ", strip=True)
                    if len(txt) > len(aciklama):
                        aciklama = txt[:1500]
            # Eğer hiç yoksa table tr'lerden teknik bilgi
            if not aciklama:
                trs = soup.select("table tr")
                parts = []
                for tr in trs[:25]:
                    cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                    if len(cells) >= 2 and 2 < len(cells[0]) < 50 and cells[1]:
                        parts.append(f"{cells[0]}: {cells[1]}")
                if parts:
                    aciklama = " · ".join(parts)[:1500]
        except Exception as e:
            log(f"[ILAN_ANALIZ] BS4 hata: {e}")
    # 3. Açıklama yetersizse erken çık (Lord "Potansiyel Elmas" durumu)
    if not aciklama or len(aciklama) < 50:
        return {"aciklama_dolu": False, "aciklama_metin": aciklama or "",
                "ilan_spec": {}, "eslesme_pct": 0}
    # 4. LLM özet (kritik özellik eşleşmesi + spec dict)
    kritik_str = ", ".join(kritik_ozellikler[:5]) if kritik_ozellikler else "model, marka"
    prompt = (
        f'Aşağıdaki Türkçe ürün ilanı açıklamasını analiz et.\n\n'
        f'KRİTİK ÖZELLİKLER (bunları arıyoruz): {kritik_str}\n\n'
        f'İLAN AÇIKLAMASI:\n{aciklama[:1200]}\n\n'
        f'GÖREV: 2 şey yap:\n'
        f'1. Açıklamadan ürünün teknik özelliklerini SADECE açıklamada VARSA çıkar '
        f'(uydurma YAPMA, sadece yazılanı al).\n'
        f'2. Kritik özelliklerden kaçı açıklamada GÖZÜKÜYOR — yüzde olarak.\n\n'
        f'SADECE şu JSON yapısında yanıt ver (markdown YOK):\n'
        f'{{"ilan_spec": {{"model": "...", "marka": "...", "ozellik1": "..."}}, '
        f'"eslesme_pct": 0-100, "yorum": "1 cümle değerlendirme"}}\n\n'
        f'JSON çıktı:'
    )
    data, raw = _llm_json_call(prompt, llama_url, max_tokens=400, temperature=0.0, timeout=45)
    spec = data.get("ilan_spec", {}) if isinstance(data, dict) else {}
    eslesme = int(data.get("eslesme_pct", 0)) if isinstance(data, dict) else 0
    eslesme = max(0, min(100, eslesme))
    log(f"[ILAN_ANALIZ] {url[-40:]} aciklama={len(aciklama)}ch spec={len(spec)} eslesme={eslesme}%")
    return {
        "aciklama_dolu": True,
        "aciklama_metin": aciklama[:600],
        "ilan_spec": spec if isinstance(spec, dict) else {},
        "eslesme_pct": eslesme,
    }


def hazine_seviye_belirle(price: float, epey_avg: float, eslesme_pct: int,
                          aciklama_dolu: bool) -> Tuple[str, str, float]:
    """FAZ-C (6 Haz 2026) — Lord doktrini 4-seviye hazine kategori.

    Returns: (tier, not_metafor, boost_ekstra)
    """
    if epey_avg <= 0 or price <= 0:
        return ("", "", 0.0)
    fiyat_oran = price / epey_avg  # 0.3 = %70 ucuz, 1.0 = denk
    # 🔴 NORMAL — fiyat denk/yakın (uyanık satıcı, hazine değil)
    if fiyat_oran > 0.8:
        return ("normal", "satıcı değer biliyor — fırsat değil", 0.0)
    # Ucuz mu (epey_avg × 0.5 alti)
    cok_ucuz = fiyat_oran < 0.5
    # 💎 POTANSİYEL ELMAS — açıklama BOŞ + ucuz (Lord metaforu)
    if cok_ucuz and not aciklama_dolu:
        return ("potansiyel_elmas",
                "çamurda elmas olabilecek bir şey — risk + potansiyel",
                1.0)
    # 🟢 ONAYLI HAZİNE — ucuz + açıklama eşleşmesi yüksek
    if cok_ucuz and eslesme_pct >= 60:
        return ("onayli", "doğrulanmış, gerçek değer", 3.0)
    # 🟡 ŞÜPHELİ HAZİNE — ucuz + açıklama eşleşmesi düşük
    if cok_ucuz and eslesme_pct < 60:
        return ("supheli", "model belirsiz, dikkatli al", 0.5)
    # Orta fiyat (0.5-0.8) — boost yok
    return ("normal", "", 0.0)


def analyze_flaws(description: str, llama_url: str = LLAMA_URL) -> Dict[str, Any]:
    """FAZ-3: 2.el ilan açıklamasından kusur tipi çıkar (LLM JSON mode).

    4 kusur tipi (kozmetik/kullanım/fonksiyonel/yapısal) → risk kesintisi (-1/-3/-5/-7).
    """
    if not description or len(description) < 20:
        return {"flaws": [], "total_kesinti": 0}

    prompt = (
        'Aşağıdaki Türkçe ilan açıklamasında 4 kusur tipinden hangileri var?\n\n'
        'KUSUR TİPLERİ:\n'
        '- "kozmetik": ufak çizik, etiket izi, boya atması\n'
        '- "kullanim": kablo ezilmiş, koltuk yıpranması, ekran çizik\n'
        '- "fonksiyonel": motor ses yapıyor, direnç ayarı bozuk\n'
        '- "yapisal": şase çatlağı, kırık, devre kartı yanık\n\n'
        'SADECE şu JSON yapısında yanıt ver (markdown YOK, açıklama YOK):\n'
        '{"flaws": [{"tip": "kozmetik", "snippet": "ilandan alıntı"}]}\n'
        'Kusur yoksa: {"flaws": []}\n\n'
        f'İLAN: {description[:1000]}\n\n'
        'JSON çıktı:'
    )
    data, raw = _llm_json_call(prompt, llama_url, max_tokens=600)
    if not data:
        return {"flaws": [], "total_kesinti": 0, "raw_preview": raw[:120]}
    flaws = data.get("flaws", [])
    total = sum(KUSUR_RISK.get(f.get("tip", ""), {}).get("kesinti", 0) for f in flaws)
    return {"flaws": flaws, "total_kesinti": total}


def evaluate_reviews(reviews: List[str], llama_url: str = LLAMA_URL) -> Dict[str, Any]:
    """FAZ-3: Yorumlardan kronik sorun çıkar (Bayesian destekli)."""
    if not reviews:
        return {"kronik_sorunlar": [], "ozet": ""}
    sample = " ".join(reviews[:20])[:2000]
    prompt = (
        'Aşağıdaki Türkçe kullanıcı yorumlarını analiz et. EN AZ 2 yorumda tekrarlayan '
        'kronik sorunları bul.\n\n'
        'SADECE şu JSON yapısında yanıt ver (markdown YOK):\n'
        '{"kronik_sorunlar": [{"sorun": "kısa açıklama", "frekans": 3}], '
        '"ozet": "1-2 cümle özet"}\n'
        'Kronik sorun yoksa: {"kronik_sorunlar": [], "ozet": "..."}\n\n'
        f'YORUMLAR:\n{sample}\n\n'
        'JSON çıktı:'
    )
    data, raw = _llm_json_call(prompt, llama_url, max_tokens=800, timeout=120)
    if not data:
        return {"kronik_sorunlar": [], "ozet": "", "raw_preview": raw[:120]}
    return {
        "kronik_sorunlar": data.get("kronik_sorunlar", []),
        "ozet": data.get("ozet", ""),
    }


def merchant_judge(listing: ProductListing, criteria: Dict[str, Any],
                   mod: str = "dengeli", llama_url: str = LLAMA_URL) -> Dict[str, Any]:
    """FAZ-3: V/R/F + kusur + yorum analizi → final master + 1-3 cümle gerekçe."""
    summary = (
        f"Ürün: {listing.title[:80]}\n"
        f"Fiyat: {listing.price} TL ({'2.el ' + listing.kondisyon if listing.is_second_hand else 'sıfır'})\n"
        f"V={listing.v_score} R={listing.r_score} F={listing.f_score} MASTER={listing.master_score}\n"
        f"Yorum: {listing.review_count} (puan {listing.rating or '?'})\n"
        f"Mod: {mod}\n"
        f"Kategori kritikleri: {', '.join((criteria.get('kritik') or [])[:6])}\n"
    )
    prompt = (
        'Aşağıdaki ürün için Lord\'a hitap eden 1-3 cümle Türkçe gerekçe yaz.\n\n'
        'SADECE şu JSON yapısında yanıt ver (markdown YOK):\n'
        '{"gerekce": "Lordum, bu ürün ... çünkü ...", "final_score": 8.5}\n\n'
        f'ÜRÜN BİLGİSİ:\n{summary}\n\n'
        'JSON çıktı:'
    )
    data, raw = _llm_json_call(prompt, llama_url, max_tokens=400, temperature=0.2, timeout=60)
    if not data:
        return {"gerekce": "(LLM gerekçe alınamadı)", "final_score": listing.master_score,
                "raw_preview": raw[:120]}
    return {
        "gerekce": data.get("gerekce", "(gerekçe boş)"),
        "final_score": data.get("final_score", listing.master_score),
    }


# ============================================================================
# Telegram 5-Mesaj Akışı (MD v3 şablonları)
# ============================================================================
def _market_msg_aydinlama(bulgu: Dict[str, Any], query: str) -> str:
    """FAZ-B 4 Haz — Aydinlama Bulgusu Telegram mesaji.
    FAZ-A revize (6 Haz): web_baglam + populer_markalar eklendi (Lord 'web bilgisi')."""
    kritik = bulgu.get("kritik", [])[:5]
    aciklama = bulgu.get("aciklama", "")[:200]
    fiyat = bulgu.get("fiyat_aralik", "")
    markalar = bulgu.get("populer_markalar", [])[:5]
    web_var = bulgu.get("web_baglam", False)
    is_fallback = "fallback" in aciklama.lower()
    src_parts = []
    if not is_fallback:
        src_parts.append("🧠 LLM")
    else:
        src_parts.append("📚 statik bilgi")
    if web_var:
        src_parts.append("🌐 web")
    src = " + ".join(src_parts)
    lines = [
        f"💡 <b>Aydınlama Bulgusu</b> ({src})",
        "",
        f"📋 Kategori: <b>{query[:60]}</b>",
        "",
        "🎯 <b>Bakman gereken kritik özellikler:</b>",
    ]
    for k in kritik:
        lines.append(f"  • {k}")
    if markalar:
        lines.append("")
        lines.append(f"🏷️ <b>Popüler markalar:</b> {' · '.join(markalar[:5])}")
    if aciklama and not is_fallback:
        lines.append("")
        lines.append(f"💭 {aciklama}")
    if fiyat:
        lines.append("")
        lines.append(f"💰 Beklenen fiyat: {fiyat}")
    return "\n".join(lines)


def _market_msg_baslangic(query: str, budget: float, top_n: int, mod: str,
                          n_kritik: int, ref_price_min: float, ref_price_max: float) -> str:
    return (
        f"🚀 <b>Kuroshin Market Master devrede!</b>\n\n"
        f"📋 Araştırma: <b>{query[:60]}</b>\n"
        f"💰 Bütçe: {budget:,.0f} TL\n"
        f"🎯 Hedef: En iyi {top_n} ürün\n"
        f"⚖️ Mod: {mod.capitalize()}\n\n"
        f"🧠 Epey'den {n_kritik} kritik parametre öğrenildi.\n"
        f"💰 Referans sıfır fiyat: {ref_price_min:,.0f} - {ref_price_max:,.0f} TL\n"
        f"⏳ Tarama başlıyor..."
    )


def _market_msg_canli_durum(site_stats: Dict[str, Dict[str, Any]], elapsed_sec: int) -> str:
    lines = ["📡 <b>Tarama Durumu</b>"]
    for site, stat in site_stats.items():
        n = stat.get("n", 0)
        durum = stat.get("durum", "...")
        emoji = "✅" if durum == "tamam" else "🕷️"
        bar_filled = min(10, n // 5)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        lines.append(f"{emoji} {site.capitalize()}: {bar} {n} ilan ({durum})")
    m, s = divmod(elapsed_sec, 60)
    lines.append(f"⏱️ Geçen süre: {m} dk {s} sn")
    return "\n".join(lines)


def _truncate_word_boundary(s: str, n: int) -> str:
    """FAZ-A (4 Haz): kelime sınırında akıllı kesim — Lord 'baslik kirpik' bug fix.
    n>=110 default. Son boslukta kes, '…' ekle."""
    if not s:
        return ""
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    last_space = cut.rfind(" ")
    # eger son boşluk yeterince ileri ise oraya kadar
    if last_space > n * 0.7:
        cut = cut[:last_space]
    return cut.rstrip(" ,.-—") + "…"


_SITE_DISPLAY = {
    "epey": "Epey", "trendyol": "Trendyol", "hepsiburada": "Hepsiburada",
    # 6 Haz Yol A: akakce ≠ Sahibinden. Akakce fiyat karşılaştırma agregatörü.
    # Lord doktrini: "akakce alternatif aramak için iyi fırsatlar sunabilir"
    # Gerçek Sahibinden hazine (2.el) için CF Turnstile bypass/Google search gerek
    "sahibinden_indirect": "akakce (fiyat keşif)",
    "cimri": "cimri.com", "akakce": "akakce.com",
}


def _market_msg_ana_rapor(listings: List[ProductListing], mod: str) -> str:
    if not listings:
        return _market_msg_fallback_hicsonuc(mod)
    lines = ["🏆 <b>MARKET MASTER RAPORU</b>", "━" * 25]
    medals = ["🥇", "🥈", "🥉"]
    for i, L in enumerate(listings[:3]):
        m = medals[i] if i < len(medals) else f"#{i+1}"
        # FAZ-A optimize (E, 6 Haz): baslik 110 → 80 (mobil okunabilir, 2 satir)
        title_clean = _truncate_word_boundary(L.title, 80)
        # HTML kacis (Telegram parse_mode=HTML)
        url_safe = (L.url or "").replace('"', '%22').replace('<', '%3C').replace('>', '%3E')
        link_part = f' · <a href="{url_safe}">🔗 İncele</a>' if url_safe and url_safe.startswith("http") else ""
        # FAZ-C: yorum sinyali (rating + foto) — varsa ek satir
        yorum_line = ""
        if L.rating:
            yorum_line = f"\n💬 ⭐ {L.rating}/5"
            if L.has_photo_review:
                yorum_line += " · 📸 fotolu yorum"
        elif L.has_photo_review:
            yorum_line = "\n💬 📸 fotolu yorum"
        # Yol A (6 Haz): akakce ucuz satıcı rozet ("hazine" terminolojisi kaldırıldı)
        # Gerçek Sahibinden hazine (CF Turnstile bypass) ileride yapılacak
        if L.is_hazine and L.hazine_iskonto_pct >= 30:
            hazine_rozet = f" 💰 <b>EN UCUZ %{L.hazine_iskonto_pct}↓</b>"
        else:
            hazine_rozet = ""
        # FAZ-G optimize: site adı insan-okur
        site_disp = _SITE_DISPLAY.get(L.site, L.site.replace("_", " ").capitalize())
        # Fix #4: alt fiyat alternatifi varsa göster
        alt_line = ""
        if L.alt_fiyat and L.alt_site:
            alt_line = f"\n🔁 Alt fiyat: <b>{L.alt_fiyat:,.0f} TL</b> ({L.alt_site})"
        # FAZ-B/C (6 Haz): Hazine analiz notu (Lord metaforu)
        hazine_not_line = ""
        if L.hazine_not:
            hazine_not_line = f"\n📝 {L.hazine_not}"
            if L.eslesme_pct:
                hazine_not_line += f" · açıklama eşleşme %{L.eslesme_pct}"
        lines.append(
            f"\n{m} <b>{i+1}. SIRA — Master Score: {L.master_score}/10</b>{hazine_rozet}\n"
            f"📌 {title_clean}\n"
            f"🏷️ {L.price:,.0f} TL"
            + (f" (sıfır referans var)" if not L.is_second_hand else f" (2.el · {L.kondisyon})")
            + alt_line + hazine_not_line + "\n"
            f"⭐ Değer: {L.v_score} | Güven: {L.r_score} | Özellik: {L.f_score}"
            + yorum_line + "\n"
            f"🌐 {site_disp}{link_part}\n"
        )
    return "\n".join(lines)


def _market_render_ascii_chart(listings: List[ProductListing]) -> str:
    """FAZ-G optimize (6 Haz) — mobil-uyumlu 10-blok progress bar + master rozet.
    Eski sutunlu tabloda mobil ekranda kayma vardı."""
    if not listings:
        return "📊 (puan diyagramı için ürün yok)"
    lines = ["📊 <b>SKOR KARŞILAŞTIRMASI</b>", ""]
    medals = ["🥇", "🥈", "🥉"]

    def _bar10(score: float) -> str:
        # 0-10 → 10 birim. ▰ dolu, ▱ boş — Telegram font'ta hizalı
        full = max(0, min(10, int(round(score))))
        return "▰" * full + "▱" * (10 - full)

    for i, L in enumerate(listings[:3]):
        m = medals[i] if i < len(medals) else "•"
        title = L.title[:32] + ("…" if len(L.title) > 32 else "")
        # Hazine rozeti varsa goster
        hzn = " 💎" if L.is_hazine else ""
        lines.append(f"{m} <b>{title}</b>{hzn}")
        lines.append(f"   Master  {_bar10(L.master_score)} <b>{L.master_score}</b>/10")
        lines.append(f"   Değer   {_bar10(L.v_score)}  {L.v_score:.1f}")
        lines.append(f"   Güven   {_bar10(L.r_score)}  {L.r_score:.1f}")
        lines.append(f"   Özellik {_bar10(L.f_score)}  {L.f_score:.1f}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _market_msg_derin_analiz(listing: ProductListing, judge_result: Dict[str, Any]) -> str:
    return (
        f"🔍 <b>Derin Analiz — {listing.title[:60]}</b>\n\n"
        f"💬 {judge_result.get('gerekce', '')[:300]}\n\n"
        f"📌 Fiyat: {listing.price:,.0f} TL\n"
        f"📊 V:{listing.v_score} R:{listing.r_score} F:{listing.f_score} → MASTER {listing.master_score}\n"
        f"🌐 Site: {listing.site}"
    )


# ============================================================================
# Hata / Fallback Mesajları (MD v3 şablon)
# ============================================================================
def _market_msg_fallback_hicsonuc(min_budget: float = 0) -> str:
    if min_budget > 0:
        return (f"🔍 Bütçene ve kriterlerine uygun ürün bulamadım. "
                f"Bütçeni biraz artırmak ister misin? (Önerilen min. bütçe: {min_budget:,.0f} TL)")
    return "🔍 Bütçene ve kriterlerine uygun ürün bulamadım. Kriterlerini gevşetmek ister misin?"


def _market_msg_fallback_site_erisilemez(site: str) -> str:
    return f"⚠️ {site}'e şu an erişilemiyor. Diğer site sonuçlarıyla devam ediyorum."


def _market_msg_fallback_zaman_asimi(found_n: int) -> str:
    return (f"⏳ Tarama uzadı. Şimdilik en iyi {found_n} sonucu gönderiyorum, "
            f"kalanını /devam komutuyla alabilirsin.")


# ============================================================================
# ANA ENTRY — chancellor `market_master` tool buraya delegate eder
# ============================================================================
def _sanitize_query(query: str, max_words: int = 6) -> str:
    """Lord direktifi FIX-ALL: model bazen query'yi sisirir (B3 bulgu).
    Stop-words ve cumle uzunlugunu kirp: 'kondisyon bisikleti almayi dusunyorum' → 'kondisyon bisikleti'."""
    if not query:
        return "kondisyon bisikleti"
    # URL slug temizle (model bazen ilan ID/slug ekler)
    cleaned = re.sub(r"\b\d{6,}-?[a-z-]*\b", "", query, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\sıİğĞüÜşŞöÖçÇ]", " ", cleaned)
    # 3 Haz 2026 FIX: Lord canli inject ornegi 'Kuroshin Market Master: kondisyon bisikleti 3000 TL butce arastir'
    # → LLM tool param 'Kuroshin butce' verdi → 'butce' stop'ta yoktu → defter/taki sonucu geldi
    stop = {
        # Niyet/eylem (eski)
        "almak", "almayi", "almayı", "almay", "dusunuyorum", "düşünüyorum", "düşünüyor",
        "icin", "için", "olan", "tipi", "bana", "uygun", "ile", "ve", "veya",
        "araştır", "arastir", "arastrir", "ara", "bul", "tara", "göster", "goster",
        "lutfen", "lütfen", "alici", "alıcı", "merhaba", "lordum",
        # Sistem/hitap kelimeler
        "kuroshin", "master", "marketmaster",
        # Para/butce kelimeleri (3 Haz — Lord canli inject bug)
        "tl", "lira", "para", "fiyat", "fiyatli", "fiyatlı",
        "butce", "butçe", "bütçe", "bütçem", "butcem", "butcesi", "bütçesi",
        "budget", "budgetla", "fiyatla", "civari", "civarı", "kadar", "yaklasik", "yaklaşık",
        # Yardimci fiil + edat (4 Haz — Task #10, runtime test FAIL fix)
        "yap", "yapsin", "yapsın", "var", "yok", "gel", "git", "sun",
        "bu", "şu", "su", "ona", "ondan", "burdan", "buradan",
        "da", "de", "ile", "icin", "için", "olarak", "kadar",
    }
    tokens = [t for t in cleaned.split() if t and t.lower() not in stop and len(t) > 2]
    out = " ".join(tokens[:max_words]).strip()
    # Anlamsiz (cok kisa veya stop-only) ise default'a dus
    if not out or len(out) < 5:
        return "kondisyon bisikleti"
    return out


def _query_to_slug(query: str) -> str:
    """Türkçe query → URL slug heuristic."""
    s = query.lower()
    tr_map = str.maketrans("ıİğĞüÜşŞöÖçÇ", "iiggUUssoocC")
    s = s.translate(tr_map).lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60]  # Epey slug genelde 30-50 char


def market_master_query(query: str, budget: float = 5000.0,
                        mod: str = "dengeli", top_n: int = 3,
                        category_slug: str = "",
                        progress_callback=None) -> Dict[str, Any]:
    """Kuroshin Market Master ana entry. FIX-ALL (3 Haz 2026) + FAZ-G stream (4 Haz):
    - query sanitize, top_n cap 5, category_slug auto-derive
    - Listing parser gerçek (JSON-LD + CSS), median referans fiyat
    - FAZ-G: progress_callback(msg) — her aşamada Telgram'a anlık update
      ('🏪 Epey araştırılıyor...', '🛒 Trendyol 6 ürün', '🕵️ Sahibinden hazine avı')
    """
    t0 = time.time()
    log_lines: List[str] = []
    def _log(msg: str):
        log_lines.append(f"[MARKET_MASTER] {msg}")
        print(log_lines[-1])

    def _progress(msg: str):
        """FAZ-G Stream: her aşamada Telgrama anlık akış. Hata yoksay."""
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception as _e:
                _log(f"progress_callback err: {_e}")

    # FIX-ALL B2: top_n cap 1-5 (model halüsinasyon 30 → 5)
    top_n = max(1, min(int(top_n or 3), 5))
    # FIX-ALL B3: query sanitize (model şişirmesi temizle)
    query_raw = query
    query = _sanitize_query(query)
    # FIX-ALL B4 + FAZ-A 4 Haz: category_slug HER ZAMAN sanitize'li query'den uret
    # (chancellor pre-slug 'kuroshin--kondisyon-bisikleti---bte' gibi bozuk veriyor → Epey 404)
    # Sanitize sonrasi query.lower() en saglam. Chancellor'dan gelen slug gozardi edilir.
    derived_slug = _query_to_slug(query)
    if not category_slug or category_slug != derived_slug:
        category_slug = derived_slug
    _log(f"query_raw={query_raw[:80]!r} → query={query!r} budget={budget} mod={mod} top_n={top_n} slug={category_slug}")

    fetcher = MarketFetcher(log_fn=_log)
    kb = KnowledgeBase(fetcher, log_fn=_log)
    scorer = MerchantScorer(log_fn=_log)

    # 1) Knowledge base — Epey kategori kriterleri (sade slug)
    kb_entry = kb.get_or_build(category_slug)
    kritik = kb_entry.get("criteria", {}).get("kritik", [])
    _log(f"KB n_kritik={len(kritik)} sample={kritik[:5]}")

    # 1.5) FAZ-B 4 Haz: Aydinlama Bulgusu — LLM kategoride kritik 3-5 ozellik
    # Fix #2 (6 Haz): Aydinlama EN BAŞA — stream'in 1. mesajı
    # FAZ-A (6 Haz revize): web_search bağlamı LLM cevabini zenginlestirir
    bulgu = aydinlama_bulgusu(query, category_slug, budget, log_fn=_log)
    _log(f"AYDINLAMA kritik={bulgu.get('kritik',[])[:5]} src={'fallback' if 'fallback' in bulgu.get('aciklama','').lower() else 'LLM'}")
    # LLM cıktısı doluysa KB kritik listesini onunla genislet
    if bulgu.get("kritik") and "fallback" not in bulgu.get("aciklama", "").lower():
        kritik = list(dict.fromkeys(list(bulgu["kritik"]) + kritik))[:10]
    msg_aydinlama = _market_msg_aydinlama(bulgu, query)
    # Aydinlama hemen şimdi yolla (stream içinde 1. sıra — Lord "Epey önce, sonra Trendyol")
    _progress(msg_aydinlama)

    # 2) Telegram MESAJ 1: Başlangıç (geçici fiyat aralığı; gerçek listing sonrası güncelleyebiliriz)
    ref_price_min, ref_price_max = budget * 0.6, budget * 1.4
    msg1 = _market_msg_baslangic(query, budget, top_n, mod, len(kritik),
                                 ref_price_min, ref_price_max)

    # 3) Multi-source crawl (FIX-ALL: gerçek JSON-LD + CSS parser)
    # FAZ-G Stream: her sitenin oncesinde ve sonrasinda Telgrama anlik update.
    # Lord doktrini: "kademe kademe akar, model dusunce surecini gosterir"
    site_stats: Dict[str, Dict[str, Any]] = {}
    listings: List[ProductListing] = []
    # FAZ-G optimize: site adi insan-okur + her sitenin başlangic mesaji silindi
    site_emoji = {"epey": "🏪", "trendyol": "🛒", "hepsiburada": "🛍️"}
    site_display = {"epey": "Epey", "trendyol": "Trendyol", "hepsiburada": "Hepsiburada"}
    site_urls = [
        ("epey.com",        f"https://www.epey.com/{category_slug}/", "epey"),
        ("trendyol.com",    f"https://www.trendyol.com/sr?q={query.replace(' ', '+')}", "trendyol"),
        ("hepsiburada.com", f"https://www.hepsiburada.com/ara?q={query.replace(' ', '+')}", "hepsiburada"),
    ]
    for site_domain, listing_url, site_short in site_urls:
        emo = site_emoji.get(site_short, "•")
        disp = site_display.get(site_short, site_short.capitalize())
        try:
            r = fetcher.fetch(listing_url)
            if r.blocked or r.status != 200:
                site_stats[site_domain] = {
                    "n": 0, "durum": f"blocked ({r.status})", "tier": r.tier,
                    "title": (r.title or "")[:60],
                }
                _progress(f"{emo} <b>{disp}</b>: ⚠️ erişim engellendi ({r.status})")
                continue
            parsed = _parse_listings_from_html(r.text, site_short, budget, limit=top_n*2, log_fn=_log)
            site_stats[site_domain] = {
                "n": len(parsed),
                "durum": "tamam" if parsed else "tamam (parse=0)",
                "tier": r.tier,
                "title": (r.title or "")[:60],
                "chars": len(r.text),
            }
            for p in parsed:
                listings.append(ProductListing(**p))
            # Stream — tek mesaj her site icin (FAZ-G optimize): X taraniyor + sonuc → birlestir
            if parsed:
                ornek = parsed[0].get("title", "")[:45]
                ratings = [x.get("rating") for x in parsed if x.get("rating")]
                foto_n = sum(1 for x in parsed if x.get("has_photo_review"))
                yorum_part = ""
                if ratings:
                    avg_r = sum(ratings) / len(ratings)
                    yorum_part = f" · ⭐ {avg_r:.1f}"
                if foto_n:
                    yorum_part += f" · 📸 {foto_n}"
                _progress(f"{emo} <b>{disp}</b>: {len(parsed)} ürün{yorum_part} — <i>{ornek}…</i>")
            else:
                _progress(f"{emo} <b>{disp}</b>: parse=0 (içerik uygun değil)")
        except Exception as e:
            site_stats[site_domain] = {"n": 0, "durum": f"hata: {str(e)[:40]}", "tier": "-"}
            _log(f"site {site_domain} hata: {e}")
            _progress(f"{emo} <b>{disp}</b>: ❌ hata — {str(e)[:60]}")

    # 4) Sahibinden indirect (FAZ-2): cimri/akakce → JSON-LD + CSS parser
    # FAZ-E (4 Haz): Bot-Anomali Cift Filtre — Epey avg × 0.05/5 esiklerle Sahibinden
    # bot/sahte ilanları ele. Lord doktrini: "1000 TL urunu 10 TL'ye atmaz".
    epey_listings_prices = [L.price for L in listings if L.site == "epey" and L.price > 0]
    epey_avg = sum(epey_listings_prices) / len(epey_listings_prices) if epey_listings_prices else 0
    # FAZ-Cookie (6 Haz): Lord cookies varsa Sahibinden direkt erişim, yoksa akakce
    sahib_cookies = _load_sahibinden_cookies()
    if sahib_cookies:
        _progress(f"🔐 <b>Sahibinden direkt</b> erişim (Lord cookies aktif, {len(sahib_cookies)} cookie)")
    elif epey_avg > 0:
        _progress(f"🔍 <b>Akakce fiyat keşfi</b> (Sahibinden cookies yok — fallback) — Epey avg {epey_avg:,.0f}₺ · bot eşik [{epey_avg*0.05:,.0f}–{epey_avg*5:,.0f}]₺")
    else:
        _progress(f"🔍 <b>Akakce fiyat keşfi</b> başladı (Sahibinden cookies yok — fallback)")
    # FAZ-Cookie: Sahibinden direkt önce dene (Lord cookies varsa)
    sahib_r = None
    sahib_direct_success = False
    if sahib_cookies:
        sahib_r = fetch_sahibinden_direct(query, log_fn=_log)
        if sahib_r and sahib_r.status == 200 and not sahib_r.blocked:
            sahib_direct_success = True
            _log("[SAHIBINDEN_DIRECT] PASS — direkt erişim")
        else:
            st = sahib_r.status if sahib_r else 0
            err = sahib_r.error if sahib_r else "None"
            _log(f"[SAHIBINDEN_DIRECT] FAIL status={st} err={err} → akakce'ye düş")
            if st == 404:
                _progress(f"⚠️ Sahibinden bu sorgu için kategori sayfası yok — akakce fallback")
            elif err == "2fa_challenge":
                _progress(f"⚠️ Sahibinden 2FA challenge — bot tespiti, cookies yenile (akakce fallback)")
            elif err == "login_redirect" or (st in (301, 302) and "login" in str(err)):
                _progress(f"⚠️ Sahibinden cookies süresi dolmuş — yeniden export gerekli (akakce fallback)")
            else:
                _progress(f"⚠️ Sahibinden erişim hatası (status={st}) — akakce fallback")
            sahib_r = None
    try:
        if not sahib_r:
            sahib_r = fetcher.fetch_sahibinden_indirect(query)
        if sahib_r.status == 200 and not sahib_r.blocked and sahib_r.text:
            # Sahibinden direkt veya akakce'ye göre parser seç
            if sahib_direct_success:
                sahib_parsed = _parse_sahibinden_listings(
                    sahib_r.text, budget, limit=top_n*2, log_fn=_log, query=query
                )
            else:
                sahib_parsed = _parse_listings_from_html(
                    sahib_r.text, "sahibinden_indirect", budget,
                    limit=top_n*2, log_fn=_log,
                )
            # FAZ-E Bot-Anomali Filter
            bot_eliminated = 0
            if epey_avg > 0:
                alt_esik = max(50.0, epey_avg * 0.05)  # 50 TL hard minimum
                ust_esik = epey_avg * 5
                kept = []
                for p in sahib_parsed:
                    if alt_esik <= p.get("price", 0) <= ust_esik:
                        kept.append(p)
                    else:
                        bot_eliminated += 1
                _log(f"[BOT_ANOMALI] Sahibinden: Epey avg={epey_avg:.0f} TL | esik [{alt_esik:.0f}-{ust_esik:.0f}] | elenen={bot_eliminated}/{len(sahib_parsed)}")
                sahib_parsed = kept
            site_stats["sahibinden.com"] = {
                "n": len(sahib_parsed),
                "durum": f"indirect/{sahib_r.tier.split('/')[-1] if '/' in sahib_r.tier else 'fail'}"
                          + (f" (bot×{bot_eliminated})" if bot_eliminated else ""),
                "tier": sahib_r.tier,
                "bot_eliminated": bot_eliminated,
                "epey_avg": int(epey_avg) if epey_avg else 0,
            }
            # FAZ-D Hazine Avi: epey_avg*0.6 altinda = hazine; yoksa bütçe*0.7 fallback
            # Lord doktrini: "Sahibinden = hazine madeni, ucuz pahali muadil bul"
            if epey_avg > 0:
                hazine_esik = epey_avg * 0.6
                ref_for_iskonto = epey_avg
            else:
                # Epey fiyatı yoksa bütçenin %70'i altı = potansiyel hazine (bütçe bazlı)
                hazine_esik = budget * 0.7 if budget > 0 else 0
                ref_for_iskonto = budget
                if hazine_esik:
                    _log(f"[HAZINE] epey_avg=0, bütçe bazlı eşik: {hazine_esik:,.0f}₺")
            for p in sahib_parsed:
                pr = p.get("price", 0)
                if hazine_esik and 0 < pr < hazine_esik:
                    p["is_hazine"] = True
                    p["hazine_iskonto_pct"] = int((1 - pr / ref_for_iskonto) * 100) if ref_for_iskonto > 0 else 0
            for p in sahib_parsed:
                listings.append(ProductListing(**p))
            # Yol A (6 Haz): "💎 HAZINE" → "💰 EN UCUZ" akakce fiyat keşif
            bot_part = f" · bot×{bot_eliminated} elendi" if bot_eliminated else ""
            ucuzlar = [p for p in sahib_parsed if p.get("is_hazine")]  # field adı sabit, anlam degisti
            # FAZ-Cookie: direkt erişim sonucu "💎 HAZINE" gerçek olur, akakce "💰 EN UCUZ"
            src_label = "Sahibinden" if sahib_direct_success else "Akakce"
            hazine_emoji = "💎" if sahib_direct_success else "💰"
            hazine_label = "HAZINE" if sahib_direct_success else "EN UCUZ"
            n_label = "ilan" if sahib_direct_success else "alternatif"
            kesif_emoji = "🕵️" if sahib_direct_success else "🔍"
            if ucuzlar:
                ornek = max(ucuzlar, key=lambda x: x.get("hazine_iskonto_pct", 0))
                extra = f" · +{len(ucuzlar)-1} daha" if len(ucuzlar) > 1 else ""
                _progress(f"{kesif_emoji} <b>{src_label}</b>: {len(sahib_parsed)} {n_label}{bot_part}\n"
                          f"{hazine_emoji} <b>{hazine_label}</b>: <i>{ornek.get('title','')[:50]}</i> → "
                          f"<b>{ornek['price']:,.0f}₺</b> · Epey avg'dan ~%{ornek['hazine_iskonto_pct']}↓{extra}")
            else:
                _progress(f"{kesif_emoji} <b>{src_label}</b>: {len(sahib_parsed)} {n_label}{bot_part} · belirgin ucuzluk yok")
        else:
            site_stats["sahibinden.com"] = {
                "n": 0, "durum": "akakce (boş)", "tier": sahib_r.tier,
            }
            _progress(f"🔍 Akakce: boş döndü ({sahib_r.tier})")
    except Exception as e:
        site_stats["sahibinden.com"] = {"n": 0, "durum": f"akakce hata: {str(e)[:30]}", "tier": "-"}
        _log(f"akakce indirect hata: {e}")
        _progress(f"🔍 Akakce: ❌ hata — {str(e)[:60]}")

    # 5) FIX-ALL: Referans fiyat gerçek listing'lerin median'ından
    if listings:
        sorted_prices = sorted(L.price for L in listings if L.price > 0)
        if sorted_prices:
            ref_price_min = sorted_prices[0]
            ref_price_max = sorted_prices[-1]
            _log(f"REF_PRICE_REAL min={ref_price_min} max={ref_price_max} (n={len(sorted_prices)})")
            # Mesaj 1'i güncelle (yeni fiyat aralığı için)
            msg1 = _market_msg_baslangic(query, budget, top_n, mod, len(kritik),
                                         ref_price_min, ref_price_max)

    # 5) Telegram MESAJ 2: Canlı durum
    msg2 = _market_msg_canli_durum(site_stats, int(time.time() - t0))

    # Fix #4 (6 Haz): Cross-site dedup — aynı marka+model farklı sitelerde tek satır
    # Imza: title'ın ilk 3 anlamlı kelimesi (noktalama/case temizle, stop-word at)
    def _model_imza(t: str) -> str:
        t = re.sub(r"[^\w\s]", " ", t.lower())
        # generic kelimeler at — marka+model anlamlı
        stop_words = {"ev", "tipi", "dikey", "yatay", "spin", "bike", "egzersiz", "bisiklet", "bisikleti",
                      "kondisyon", "fitness", "kardiyo", "mini", "küçük", "kucuk", "boy", "ve"}
        words = [w for w in t.split() if len(w) > 2 and w not in stop_words][:3]
        return " ".join(words)
    if len(listings) > 1:
        gruplar: Dict[str, List[ProductListing]] = {}
        for L in listings:
            imza = _model_imza(L.title)
            gruplar.setdefault(imza, []).append(L)
        merged: List[ProductListing] = []
        for imza, grup in gruplar.items():
            if len(grup) == 1 or not imza:
                merged.extend(grup)
                continue
            # En ucuz olanı SECME — score sonra hesaplanacak; şimdilik ilk geleni baz al
            grup_by_price = sorted(grup, key=lambda x: x.price)
            ana = grup_by_price[0]  # en ucuz, master ile sıralanacak sonra
            alt = grup_by_price[1] if len(grup_by_price) > 1 else None
            if alt and alt.price > ana.price:
                ana.alt_fiyat = alt.price
                ana.alt_site = _SITE_DISPLAY.get(alt.site, alt.site).split(" ")[0]
            merged.append(ana)
            _log(f"[DEDUP] '{imza}' → {len(grup)} ilan → 1 (alt: {alt.price if alt else '-'}₺ {alt.site if alt else '-'})")
        if len(merged) < len(listings):
            _log(f"[DEDUP] toplam {len(listings)} → {len(merged)} ürün (cross-site)")
            listings = merged

    # 6) Puanla + sırala
    if listings:
        ref_price = (ref_price_min + ref_price_max) / 2
        listings = scorer.score_all(listings, ref_price, kritik, mod)
        # FAZ-D (7 Haz): Lord düşünce profili — site önceliği, marka, bot ceza
        lord_profil = _load_lord_profil()
        if lord_profil:
            _progress(f"👤 <b>Lord profili aktif</b> — Sahibinden öncelikli, min ⭐{lord_profil.get('yorum_bot_esik',{}).get('min_yildiz',4.0)}, marka tercihi {len(lord_profil.get('marka_tercih',{}).get('tanidik_markalar',[]))}")
            listings = _lord_skor_ayarla(listings, log_fn=_log)
            # Yeniden sırala (Lord ayarı sonrası)
            listings = sorted(listings, key=lambda x: (
                -x.master_score, -x.hazine_iskonto_pct, -(x.rating or 0),
                x.price if x.price > 0 else 999999,
            ))
        # FAZ-D Hazine Boost: Sahibinden ilanlarinda epey_avg*0.6 alti = HAZINE
        # master_score'a +1.5 boost (max 10). Lord doktrini "cam gibi cikar".
        hazine_boost_n = 0
        for L in listings:
            if L.is_hazine:
                old = L.master_score
                L.master_score = round(min(10.0, L.master_score + 1.5), 2)
                hazine_boost_n += 1
        if hazine_boost_n:
            _log(f"UCUZ BOOST: {hazine_boost_n} ilana +1.5 master_score uygulandi (akakce en ucuz)")
            # Sırala YENIDEN — boost sonrasi hazineler ust siralara çıkabilir
            listings = sorted(listings, key=lambda x: x.master_score, reverse=True)
            # Yol A: "hazine" → "en ucuz satıcı" (Lord doktrini)
            _progress(f"💰 <b>{hazine_boost_n} ucuz alternatif</b> üst sıraya alındı (akakce fiyat avantajı)")

        # FAZ-B (6 Haz Yol A): Akakce ilan açıklama LLM analizi — fiyat keşfi için değerli
        # 4-seviye karar AKAKCE için anlamsız (Onaylı/Şüpheli/Elmas sadece gerçek Sahibinden)
        # Akakce için sadece "açıklama incelendi" + spec özet, hazine terminolojisi YOK
        ucuz_adaylari = [L for L in listings if L.is_hazine and L.url][:3]
        if ucuz_adaylari:
            _progress(f"🔍 <b>{len(ucuz_adaylari)} ucuz adayı</b> akakce açıklaması inceleniyor…")
            for L in ucuz_adaylari:
                analiz = sahibinden_ilan_analiz(L.url, kritik, log_fn=_log)
                L.aciklama_dolu = analiz.get("aciklama_dolu", False)
                L.ilan_spec = analiz.get("ilan_spec", {})
                L.eslesme_pct = analiz.get("eslesme_pct", 0)
                short_title = L.title[:45]
                # Yol A: "Onaylı/Şüpheli/Elmas" yerine sadece bilgilendirme
                if L.aciklama_dolu and L.eslesme_pct >= 60:
                    _progress(f"✓ <i>{short_title}…</i> — akakce açıklamasında özellikler tutuyor (%{L.eslesme_pct})")
                    L.hazine_not = f"akakce açıklama eşleşmesi yüksek %{L.eslesme_pct}"
                elif L.aciklama_dolu:
                    _progress(f"⚠️ <i>{short_title}…</i> — akakce açıklamada özellikler kısıtlı (%{L.eslesme_pct})")
                    L.hazine_not = f"akakce açıklama eşleşme düşük %{L.eslesme_pct}"
                else:
                    _progress(f"📭 <i>{short_title}…</i> — akakce sayfasında detaylı açıklama yok")
                    L.hazine_not = "akakce sayfasında detay yok — alternatif fiyat olarak değerlendir"
            # Yeniden sırala (skor + ucuz)
            listings = sorted(listings, key=lambda x: (
                -x.master_score, -x.hazine_iskonto_pct, -(x.rating or 0),
                x.price if x.price > 0 else 999999,
            ))

    # 7) Telegram MESAJ 3: Ana rapor (top_n)
    msg3 = _market_msg_ana_rapor(listings[:top_n], mod)

    # 8) Telegram MESAJ 4: ASCII diyagram
    msg4 = _market_render_ascii_chart(listings[:top_n])

    elapsed = round(time.time() - t0, 1)
    _log(f"results={len(listings)} elapsed={elapsed}s top_score={listings[0].master_score if listings else 'N/A'}")

    # FAZ-G optimize + Fix #2 (6 Haz): Aydinlama stream'in başına alındı.
    # Final messages = 2 mesaj (Ana Rapor + ASCII) — Aydınlama stream içinde 1. sıraya
    return {
        "messages": [msg3, msg4],
        "listings": [
            {"title": L.title, "price": L.price, "url": L.url, "site": L.site,
             "rating": L.rating, "review_count": L.review_count,
             "has_photo_review": L.has_photo_review,
             "is_hazine": L.is_hazine, "hazine_iskonto_pct": L.hazine_iskonto_pct,
             # FAZ-B/C: 4-seviye hazine + ilan analizi
             "hazine_tier": L.hazine_tier, "hazine_not": L.hazine_not,
             "aciklama_dolu": L.aciklama_dolu, "eslesme_pct": L.eslesme_pct,
             "ilan_spec": L.ilan_spec,
             "v": L.v_score, "r": L.r_score, "f": L.f_score, "master": L.master_score}
            for L in listings[:top_n]
        ],
        "elapsed_sec": elapsed,
        "meta": {
            "query": query, "budget": budget, "mod": mod, "top_n": top_n,
            "n_kritik": len(kritik),
            "aydinlama": bulgu,
            "site_stats": site_stats,
        },
        "log_lines": log_lines,
    }


if __name__ == "__main__":
    # Standalone test (sadece offline parse + scoring kanıtı)
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="kondisyon bisikleti")
    ap.add_argument("--budget", type=float, default=5000.0)
    ap.add_argument("--mod", default="dengeli", choices=list(MOD_WEIGHTS.keys()))
    ap.add_argument("--top-n", type=int, default=3)
    args = ap.parse_args()
    result = market_master_query(args.query, args.budget, args.mod, args.top_n)
    print("\n=== MESSAGES ===")
    for m in result["messages"]:
        print(m, "\n---")
    print("\n=== META ===")
    print(json.dumps(result["meta"], ensure_ascii=False, indent=2))
