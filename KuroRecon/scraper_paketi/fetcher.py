"""
Resilient HTTP fetcher — anti-bot bypass katmanı.
Kuroshin scraping altyapısından izole edilmiştir. Bağımlılık yok.

Desteklenen modlar:
  static     — curl_cffi TLS impersonate (birincil) + requests (fallback)
  playwright — Chromium JS-render (Trendyol, Epey gibi CSR siteler için)
"""
from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Birincil: curl_cffi (TLS/JA3 fingerprint impersonate — Akamai/CF bypass)
try:
    from curl_cffi import requests as _cc
    _HAS_CURL = True
except ImportError:
    _HAS_CURL = False

# Fallback: standart requests
import requests as _req
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Opsiyonel: Playwright (JS-render için)
try:
    from playwright.sync_api import sync_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False


# ---------------------------------------------------------------------------
# User-Agent havuzu (Chrome 130+/Firefox 132/Edge 131 — dengeli)
# ---------------------------------------------------------------------------
_UA_POOL: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

# Bilinen anti-bot sistemlerinin HARD-BLOCK imzaları.
# Sadece sayfanın gerçekten engellendiğini gösteren spesifik stringler —
# cookie adları veya JS değişkenleri gibi normal sayfalarda da geçen geniş
# patternler buraya GİRMEZ (false-positive önlemi).
_ANTIBOT_PATTERNS = [
    ("Cloudflare",  r"(Just a moment\.\.\.|Checking your browser|cf_chl_opt|cf_chl_prog)"),
    ("DataDome",    r"datadome\.co/.*blocked"),
    ("PerimeterX",  r"px-captcha"),
    ("reCAPTCHA",   r"recaptcha/api\.js"),
    ("Turnstile",   r"challenges\.cloudflare\.com/turnstile"),
    ("Sahibinden",  r"(olağandışı bir erişim|otomatik erişim tespit|Destek kodu:?\s*GW)"),
]

# Soft-detect: sayfa içeriği büyükse gerçek block değil, sadece bilgi amaçlı log
_ANTIBOT_SOFT_PATTERNS = [
    ("cf-cookie",   r"(__cf_bm|cf-ray)"),
    ("akamai-cookie", r"(ak_bmsc|_abck)"),
]
_HARD_BLOCK_MIN_SIZE = 50_000  # 50KB üzeri sayfa + soft pattern → block DEĞİL


@dataclass
class FetchResult:
    url: str
    status_code: int
    html: str
    elapsed_s: float = 0.0
    attempts: int = 1
    blocked: bool = False
    antibot: List[str] = field(default_factory=list)
    error: str = ""


def _random_ua() -> str:
    return random.choice(_UA_POOL)


def _build_headers(ua: str, referer: Optional[str] = None,
                   extra: Optional[Dict] = None) -> Dict[str, str]:
    is_chrome = "Chrome" in ua and "Edg" not in ua
    h = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
    }
    if is_chrome:
        h.update({
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none" if not referer else "cross-site",
            "Sec-Fetch-User": "?1",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        })
    if referer:
        h["Referer"] = referer
    if extra:
        h.update(extra)
    return h


def _detect_antibot(html: str, resp_headers: Dict) -> List[str]:
    """
    Gerçek HARD-BLOCK tespiti.
    Büyük sayfalar (>50KB) + sadece cookie/header imzası → block DEĞİL.
    """
    hits = []
    html_len = len(html or "")
    sample = (html or "")[:8000]
    hdr_str = " ".join(f"{k}:{v}" for k, v in resp_headers.items())

    # Hard-block patternleri — hem HTML hem header'da ara
    for name, pattern in _ANTIBOT_PATTERNS:
        if re.search(pattern, sample, re.IGNORECASE) or re.search(pattern, hdr_str, re.IGNORECASE):
            hits.append(name)

    # Soft patternler: sadece sayfa küçükse (<50KB) block say
    # Büyük sayfada Akamai/CF cookie imzası bulunması normal — içerik geldiyse block değil
    if html_len < _HARD_BLOCK_MIN_SIZE:
        for name, pattern in _ANTIBOT_SOFT_PATTERNS:
            if re.search(pattern, sample, re.IGNORECASE) or re.search(pattern, hdr_str, re.IGNORECASE):
                hits.append(name)

    return list(dict.fromkeys(hits))


def _load_cookies(cookie_file: Optional[str]) -> Dict[str, str]:
    """JSON veya Netscape formatında cookie dosyası yükle."""
    if not cookie_file:
        return {}
    p = Path(cookie_file)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # Netscape / editthiscookie format: [{name, value, domain, ...}]
            return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


class PaketFetcher:
    """
    Müşteriye teslim edilebilir HTTP fetcher.

    Kullanım:
        f = PaketFetcher(delay_min=3, delay_max=8, cookie_file="cookies.json")
        r = f.get("https://www.sahibinden.com/otomobil-ford-focus")
        print(r.status_code, r.blocked, len(r.html))
    """

    def __init__(
        self,
        delay_min: float = 3.0,
        delay_max: float = 8.0,
        timeout: float = 30.0,
        max_retries: int = 3,
        proxy: str = "",
        cookie_file: Optional[str] = None,
        user_agent: str = "auto",
    ):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.timeout = timeout
        self.max_retries = max_retries
        self.proxy = proxy or ""
        self.cookies = _load_cookies(cookie_file)
        self._fixed_ua = None if user_agent == "auto" else user_agent
        self._proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        # requests fallback session
        retry = Retry(total=max_retries, backoff_factor=1.5,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=frozenset(["GET"]),
                      respect_retry_after_header=True)
        adapter = HTTPAdapter(max_retries=retry)
        self._session = _req.Session()
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def _ua(self) -> str:
        return self._fixed_ua or _random_ua()

    def _sleep(self):
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    def get(self, url: str, referer: Optional[str] = None,
            mode: str = "static") -> FetchResult:
        """
        URL'yi fetch et.
        mode: 'static' (curl_cffi/requests) veya 'playwright'
        """
        if mode == "playwright":
            return self._get_playwright(url)
        return self._get_static(url, referer=referer)

    def _get_static(self, url: str, referer: Optional[str] = None) -> FetchResult:
        ua = self._ua()
        headers = _build_headers(ua, referer=referer)
        t0 = time.time()

        # curl_cffi birincil
        if _HAS_CURL:
            for attempt in range(1, self.max_retries + 2):
                try:
                    r = _cc.get(
                        url, impersonate="chrome124",
                        headers=headers, cookies=self.cookies,
                        proxies=self._proxies, timeout=self.timeout,
                        allow_redirects=True,
                    )
                    html = r.text
                    antibot = _detect_antibot(html, dict(r.headers))
                    blocked = bool(antibot) or r.status_code in (403, 429)
                    return FetchResult(
                        url=url, status_code=r.status_code, html=html,
                        elapsed_s=round(time.time() - t0, 2),
                        attempts=attempt, blocked=blocked, antibot=antibot,
                    )
                except Exception as e:
                    if attempt <= self.max_retries:
                        time.sleep(1.5 ** attempt + random.uniform(0.3, 0.8))
                    else:
                        return FetchResult(url=url, status_code=0, html="",
                                           elapsed_s=round(time.time() - t0, 2),
                                           attempts=attempt, blocked=True,
                                           error=str(e)[:200])

        # requests fallback
        try:
            r = self._session.get(url, headers=headers, cookies=self.cookies,
                                  proxies=self._proxies, timeout=self.timeout)
            html = r.text
            antibot = _detect_antibot(html, dict(r.headers))
            blocked = bool(antibot) or r.status_code in (403, 429)
            return FetchResult(url=url, status_code=r.status_code, html=html,
                               elapsed_s=round(time.time() - t0, 2),
                               blocked=blocked, antibot=antibot)
        except Exception as e:
            return FetchResult(url=url, status_code=0, html="",
                               elapsed_s=round(time.time() - t0, 2),
                               blocked=True, error=str(e)[:200])

    def _get_playwright(self, url: str) -> FetchResult:
        if not _HAS_PLAYWRIGHT:
            return FetchResult(url=url, status_code=0, html="",
                               blocked=True, error="playwright kurulu değil: pip install playwright && playwright install chromium")
        t0 = time.time()
        html = ""
        status = 0
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=[
                    "--no-sandbox", "--disable-blink-features=AutomationControlled",
                ])
                ctx = browser.new_context(
                    user_agent=self._ua(),
                    locale="tr-TR",
                    extra_http_headers={"Accept-Language": "tr-TR,tr;q=0.9"},
                )
                if self.cookies:
                    ctx.add_cookies([
                        {"name": k, "value": v, "domain": ".sahibinden.com", "path": "/"}
                        for k, v in self.cookies.items()
                    ])
                page = ctx.new_page()
                resp = page.goto(url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000))
                status = resp.status if resp else 0
                page.wait_for_timeout(2500)
                html = page.content()
                browser.close()
        except Exception as e:
            return FetchResult(url=url, status_code=0, html="",
                               elapsed_s=round(time.time() - t0, 2),
                               blocked=True, error=str(e)[:200])
        antibot = _detect_antibot(html, {})
        return FetchResult(url=url, status_code=status, html=html,
                           elapsed_s=round(time.time() - t0, 2),
                           blocked=bool(antibot), antibot=antibot)
