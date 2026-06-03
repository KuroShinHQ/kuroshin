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

# Local llama-server endpoint (kuroshin standard)
LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"

# Persisted state
KB_CACHE_PATH = Path("/mnt/c/Kuroshin/memory/category_criteria.json")
KB_CACHE_TTL_HOURS = 24

# ============================================================================
# DALGA-6 Smart Routing Tablosu (FAZ-0 prob kanıtı ile aligned)
# 4 hedef site: epey.com + trendyol.com + hepsiburada.com + sahibinden.com
# ============================================================================
# Test sonuçları (2 Haz 2026 19:53):
#   epey.com         → curl_cffi impersonate="chrome124" → 200, 196K char  🟢
#   trendyol.com     → curl_cffi impersonate="chrome124" → 200, 522K char  🟢
#   hepsiburada.com  → curl_cffi impersonate="chrome124" → 200, 3.8M char (Akamai aşıldı!) 🟢
#   sahibinden.com   → LOGIN ZORUNLU 2026 policy → indirect (Lord "login yok")
SITE_FETCHER: Dict[str, Tuple[str, str]] = {
    "epey.com":        ("curl_cffi",     "chrome124"),
    "trendyol.com":    ("curl_cffi",     "chrome124"),
    "hepsiburada.com": ("curl_cffi",     "chrome124"),  # Akamai aşıldı
    "sahibinden.com":  ("indirect",      "google_snippet"),  # Lord doktrini: login YOK
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
    """Tek bir ürün ilanı (3 siteden veya Sahibinden indirect)."""
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
        elif tier == "curl_cffi":
            return self._fetch_curlcffi(url, domain, profile)
        elif tier == "cloudscraper":
            return self._fetch_cloudscraper(url, domain)
        else:
            return FetchResult(url=url, status=0, error=f"Bilinmeyen tier: {tier}")

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
        """Epey kategori sayfasından kritik özellikleri çıkar."""
        url = f"https://www.epey.com/{category_slug}/"
        r = self.fetcher.fetch(url)
        if r.status != 200 or not r.text:
            self.log(f"[KB] Epey fetch FAIL: {r.error or r.status}")
            return {"kritik": [], "_fallback": True}

        criteria = {"kritik": [], "source_url": url}
        if BeautifulSoup is not None:
            try:
                soup = BeautifulSoup(r.text, "html.parser")
                # Epey filtre sidebar özellik adları (genelde h3/h4 veya .filtre)
                for tag in soup.select("h3, h4, .filtre-baslik, .ozellik-baslik")[:30]:
                    txt = tag.get_text(strip=True)
                    if 3 <= len(txt) <= 50 and not any(s in txt.lower() for s in ["fiyat", "marka", "satıcı"]):
                        criteria["kritik"].append(txt)
            except Exception as e:
                self.log(f"[KB] BS4 parse hata: {e}")

        # LLM ile destekli kritik özellik öneri (opsiyonel — Web kriter)
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
        """Feature/Özellik uygunluğu 0-10."""
        if not kritik_ozellikler:
            return 5.0
        toplam = len(kritik_ozellikler)
        karsilanan = 0
        listing_features_str = " ".join(
            [str(v).lower() for v in listing.features.values()] +
            [listing.description.lower(), listing.title.lower()]
        )
        for kriter in kritik_ozellikler:
            if kriter.lower() in listing_features_str:
                karsilanan += 1
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
        """Tüm ürünleri puanla + master_score'a göre sırala (büyükten küçüğe)."""
        for L in listings:
            L.v_score = self.calc_v_score(L, ref_price, L.is_second_hand)
            L.r_score = self.calc_r_score(L)
            L.f_score = self.calc_f_score(L, kritik_ozellikler)
            L.master_score = self.calc_master_score(L, mod)
        return sorted(listings, key=lambda x: x.master_score, reverse=True)


# ============================================================================
# FAZ-3 STUB'ları — LLM Reasoning (Tüccar Zekası)
# ============================================================================
def analyze_flaws(description: str, llama_url: str = LLAMA_URL) -> Dict[str, Any]:
    """FAZ-3: 2.el ilan açıklamasından kusur tipi çıkar (LLM JSON mode).

    4 kusur tipi (kozmetik/kullanım/fonksiyonel/yapısal) → risk kesintisi (-1/-3/-5/-7).
    """
    if not description or len(description) < 20:
        return {"flaws": [], "total_kesinti": 0}

    prompt = (
        "İlan açıklamasını analiz et. Aşağıdaki 4 kusur tipinden hangileri var?\n"
        "  - kozmetik: ufak çizik, etiket izi, boya atması\n"
        "  - kullanim: kablo ezilmiş, koltuk yıpranması\n"
        "  - fonksiyonel: motor sesli, direnç ayarı bozuk\n"
        "  - yapisal: şase çatlağı, kırık\n"
        "SADECE ham JSON döndür: {\"flaws\": [{\"tip\": \"kozmetik\", \"snippet\": \"...\"}]}\n"
        f"\nİlan: {description[:1000]}\n"
    )
    try:
        import requests
        r = requests.post(llama_url, json={
            "model": "local",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600, "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }, timeout=60)
        raw = r.json()["choices"][0]["message"]["content"]
        data = json.loads(raw)
        flaws = data.get("flaws", [])
        total = sum(KUSUR_RISK.get(f.get("tip", ""), {}).get("kesinti", 0) for f in flaws)
        return {"flaws": flaws, "total_kesinti": total}
    except Exception as e:
        return {"flaws": [], "total_kesinti": 0, "error": str(e)[:120]}


def evaluate_reviews(reviews: List[str], llama_url: str = LLAMA_URL) -> Dict[str, Any]:
    """FAZ-3: Yorumlardan kronik sorun çıkar (Bayesian destekli)."""
    if not reviews:
        return {"kronik_sorunlar": [], "ozet": ""}
    sample = " ".join(reviews[:20])[:2000]
    prompt = (
        "Yorumları analiz et. Tekrarlayan kronik sorunlar (>2 yorumda geçen) varsa listele.\n"
        "SADECE ham JSON: {\"kronik_sorunlar\": [{\"sorun\": \"...\", \"frekans\": N}], \"ozet\": \"...\"}\n"
        f"\nYorumlar: {sample}\n"
    )
    try:
        import requests
        r = requests.post(llama_url, json={
            "model": "local",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800, "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }, timeout=90)
        raw = r.json()["choices"][0]["message"]["content"]
        return json.loads(raw)
    except Exception as e:
        return {"kronik_sorunlar": [], "ozet": "", "error": str(e)[:120]}


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
        "Aşağıdaki ürün için 1-3 cümle Türkçe gerekçe yaz (Lord'a hitap). "
        "JSON: {\"gerekce\": \"...\", \"final_score\": <float>}\n"
        f"\n{summary}"
    )
    try:
        import requests
        r = requests.post(llama_url, json={
            "model": "local",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400, "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }, timeout=60)
        raw = r.json()["choices"][0]["message"]["content"]
        return json.loads(raw)
    except Exception as e:
        return {"gerekce": "(LLM gerekçe alınamadı)", "final_score": listing.master_score,
                "error": str(e)[:120]}


# ============================================================================
# Telegram 5-Mesaj Akışı (MD v3 şablonları)
# ============================================================================
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


def _market_msg_ana_rapor(listings: List[ProductListing], mod: str) -> str:
    if not listings:
        return _market_msg_fallback_hicsonuc(mod)
    lines = ["🏆 <b>MARKET MASTER RAPORU</b>", "━" * 25]
    medals = ["🥇", "🥈", "🥉"]
    for i, L in enumerate(listings[:3]):
        m = medals[i] if i < len(medals) else f"#{i+1}"
        lines.append(
            f"\n{m} <b>{i+1}. SIRA — Master Score: {L.master_score}/10</b>\n"
            f"📌 {L.title[:80]}\n"
            f"🏷️ {L.price:,.0f} TL"
            + (f" (sıfır referans var)" if not L.is_second_hand else f" (2.el · {L.kondisyon})") + "\n"
            f"⭐ Değer: {L.v_score} | Güven: {L.r_score} | Özellik: {L.f_score}\n"
            f"🌐 Site: {L.site}\n"
        )
    return "\n".join(lines)


def _market_render_ascii_chart(listings: List[ProductListing]) -> str:
    """ASCII puan diyagramı (Unicode block characters)."""
    if not listings:
        return "📊 (puan diyagramı için ürün yok)"
    lines = ["📊 <b>PUAN KARŞILAŞTIRMASI (1-10)</b>", ""]
    lines.append(f"{'Ürün':<22} {'Değer':>7} {'Güven':>7} {'Özellik':>8}  MASTER")
    medals = ["🥇", "🥈", "🥉"]
    for i, L in enumerate(listings[:3]):
        m = medals[i] if i < len(medals) else "•"
        name = (L.title[:18] + "…") if len(L.title) > 18 else L.title.ljust(20)
        def bar(score: float) -> str:
            full = int(score // 1)
            half = "▌" if (score - full) >= 0.5 else ""
            return ("█" * full + half).ljust(7)
        lines.append(f"{m} {name:<19} {bar(L.v_score)} {bar(L.r_score)} {bar(L.f_score)}  <b>{L.master_score}</b>")
    return "\n".join(lines)


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
def market_master_query(query: str, budget: float = 5000.0,
                        mod: str = "dengeli", top_n: int = 3,
                        category_slug: str = "kondisyon-bisikleti") -> Dict[str, Any]:
    """Kuroshin Market Master ana entry.

    Args:
      query: kullanıcı sorgusu (örn: "kondisyon bisikleti")
      budget: TL (float)
      mod: butce|guven|performans|dengeli
      top_n: dönecek ürün sayısı (default 3)
      category_slug: Epey URL slug (örn: "kondisyon-bisikleti")

    Returns:
      {"messages": [...], "listings": [...], "elapsed_sec": N, "meta": {...}}
    """
    t0 = time.time()
    log_lines: List[str] = []
    def _log(msg: str):
        log_lines.append(f"[MARKET_MASTER] {msg}")
        print(log_lines[-1])

    _log(f"query={query!r} budget={budget} mod={mod} top_n={top_n} category={category_slug}")

    fetcher = MarketFetcher(log_fn=_log)
    kb = KnowledgeBase(fetcher, log_fn=_log)
    scorer = MerchantScorer(log_fn=_log)

    # 1) Knowledge base — Epey kategori kriterleri
    kb_entry = kb.get_or_build(category_slug)
    kritik = kb_entry.get("criteria", {}).get("kritik", [])
    _log(f"KB n_kritik={len(kritik)} sample={kritik[:5]}")

    # 2) Referans fiyat (Epey listing min/max — placeholder şu an)
    # FAZ-1 MVP: tek fetch'ten basit aralık tahmini. FAZ-1.1'de listing parser eklenecek.
    ref_url = f"https://www.epey.com/{category_slug}/"
    ref_fetch = fetcher.fetch(ref_url)
    ref_price_min, ref_price_max = budget * 0.6, budget * 1.4  # geçici tahmin
    _log(f"Epey ref fetch status={ref_fetch.status} chars={len(ref_fetch.text)}")

    # 3) Telegram MESAJ 1: Başlangıç
    msg1 = _market_msg_baslangic(query, budget, top_n, mod, len(kritik),
                                 ref_price_min, ref_price_max)

    # 4) Multi-source crawl (Epey + Trendyol + HB direct, Sahibinden indirect FAZ-2 stub)
    site_stats: Dict[str, Dict[str, Any]] = {}
    listings: List[ProductListing] = []

    # FAZ-1 MVP: 3 site listing parser stubs (FAZ-1.1'de detaylanır)
    for site_domain, listing_url in [
        ("epey.com",        f"https://www.epey.com/{category_slug}/"),
        ("trendyol.com",    f"https://www.trendyol.com/sr?q={query.replace(' ', '+')}"),
        ("hepsiburada.com", f"https://www.hepsiburada.com/ara?q={query.replace(' ', '+')}"),
    ]:
        try:
            r = fetcher.fetch(listing_url)
            site_stats[site_domain] = {
                "n": 0 if r.blocked else 1,  # FAZ-1.1: gerçek parse
                "durum": "blocked" if r.blocked else "tamam",
                "tier": r.tier,
                "title": r.title[:60],
            }
            if not r.blocked and r.status == 200:
                # FAZ-1.1 placeholder: tek dummy listing (gerçek parse FAZ-1.1)
                listings.append(ProductListing(
                    title=f"[{site_domain}] {r.title or query}",
                    price=budget * 0.85,  # geçici
                    url=listing_url,
                    site=site_domain.replace(".com", ""),
                    rating=4.3, review_count=120,
                    features={"epey_url": listing_url},
                ))
        except Exception as e:
            site_stats[site_domain] = {"n": 0, "durum": f"hata: {str(e)[:30]}", "tier": "-"}

    # Sahibinden FAZ-2 stub
    sahib_r = fetcher.fetch("https://www.sahibinden.com/")
    site_stats["sahibinden.com"] = {
        "n": 0, "durum": "indirect (FAZ-2)", "tier": sahib_r.tier,
    }

    # 5) Telegram MESAJ 2: Canlı durum
    msg2 = _market_msg_canli_durum(site_stats, int(time.time() - t0))

    # 6) Puanla + sırala
    if listings:
        ref_price = (ref_price_min + ref_price_max) / 2
        listings = scorer.score_all(listings, ref_price, kritik, mod)

    # 7) Telegram MESAJ 3: Ana rapor (top_n)
    msg3 = _market_msg_ana_rapor(listings[:top_n], mod)

    # 8) Telegram MESAJ 4: ASCII diyagram
    msg4 = _market_render_ascii_chart(listings[:top_n])

    elapsed = round(time.time() - t0, 1)
    _log(f"results={len(listings)} elapsed={elapsed}s top_score={listings[0].master_score if listings else 'N/A'}")

    return {
        "messages": [msg1, msg2, msg3, msg4],
        "listings": [
            {"title": L.title, "price": L.price, "url": L.url, "site": L.site,
             "v": L.v_score, "r": L.r_score, "f": L.f_score, "master": L.master_score}
            for L in listings[:top_n]
        ],
        "elapsed_sec": elapsed,
        "meta": {
            "query": query, "budget": budget, "mod": mod, "top_n": top_n,
            "n_kritik": len(kritik),
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
