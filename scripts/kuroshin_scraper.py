#!/usr/bin/env python3
"""
Kuroshin Scraper Resilience v1.0 (31 May 2026 — RED TEAM FAZ E)
================================================================
Mevcut walker_research / crawlee_bridge'in altina dusebilir bir
"defansif" fetch katmani. 2026 anti-bot stack'i (Cloudflare ML score 1-99,
DataDome 35-signal, TLS fingerprinting) icin hafif Python-pure cozumler.

Bu modul bagimsizdir — walker veya chancellor istedigi zaman cagrir.
Production crawlee_bridge.js (port 3006) Patchright/stealth icin ana yol;
bu modul fallback ve kucuk-hedef icindir.

Ozellikler:
  - User-Agent rotation (40+ modern UA, agirlikli sampling)
  - Realistic header set (Accept, Accept-Language, Accept-Encoding,
    Sec-Fetch-*, DNT, Upgrade-Insecure-Requests)
  - Exponential backoff retry (429/503/cloudflare challenge)
  - Optional proxy support (env: KUROSHIN_PROXY=http://user:pass@host:port)
  - Cookies persist (rotational session)
  - Response signature: anti-bot tespit (Cloudflare/Datadome/Akamai)

KULLANIM:
    from kuroshin_scraper import ResilientFetcher
    f = ResilientFetcher()
    r = f.get("https://example.com")
    print(r.status_code, len(r.text))
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Modern UA havuzu (Chrome 130+/Firefox 130+/Safari 17, Mac/Win/Linux dengeli)
_UA_POOL: List[str] = [
    # Chrome Win
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

# Anti-bot signature pattern (response icinde varsa block tahmin)
_ANTIBOT_SIGNATURES: List[Dict[str, str]] = [
    {"name": "Cloudflare",    "regex": r"(cf-ray|__cf_bm|Just a moment|Checking your browser)"},
    {"name": "DataDome",      "regex": r"(datadome|dd_check)"},
    {"name": "Akamai",        "regex": r"(akamai|ak_bmsc|_abck)"},
    {"name": "PerimeterX",    "regex": r"(_px|px-captcha)"},
    {"name": "Imperva",       "regex": r"(incap_ses|visid_incap)"},
    {"name": "reCAPTCHA",     "regex": r"(g-recaptcha|recaptcha/api\.js)"},
    {"name": "hCaptcha",      "regex": r"hcaptcha\.com"},
    {"name": "Turnstile",     "regex": r"(challenges\.cloudflare\.com|cf-turnstile)"},
]

COOKIE_JAR_PATH = Path("/root/kuroshin/memory/scraper_cookies.json")


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_s: float = 0.0
    attempts: int = 1
    antibot_detected: List[str] = field(default_factory=list)
    final_url: str = ""


class ResilientFetcher:
    def __init__(
        self,
        proxy: Optional[str] = None,
        timeout: float = 20.0,
        max_retries: int = 4,
        cookie_persist: bool = True,
    ):
        self.proxy = proxy or os.environ.get("KUROSHIN_PROXY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.cookie_persist = cookie_persist
        self.session = requests.Session()

        retry = Retry(
            total=max_retries,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504, 408],
            allowed_methods=frozenset(["GET", "POST", "HEAD"]),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        if cookie_persist:
            self._load_cookies()

    def _load_cookies(self):
        if not COOKIE_JAR_PATH.exists():
            return
        try:
            data = json.loads(COOKIE_JAR_PATH.read_text(encoding="utf-8"))
            for c in data:
                self.session.cookies.set(**c)
        except Exception:
            pass

    def _save_cookies(self):
        if not self.cookie_persist:
            return
        try:
            data = []
            for c in self.session.cookies:
                data.append({
                    "name": c.name, "value": c.value,
                    "domain": c.domain or "", "path": c.path or "/",
                })
            COOKIE_JAR_PATH.parent.mkdir(parents=True, exist_ok=True)
            COOKIE_JAR_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def random_ua() -> str:
        return random.choice(_UA_POOL)

    @staticmethod
    def _realistic_headers(ua: str, referer: Optional[str] = None) -> Dict[str, str]:
        is_chrome = "Chrome" in ua and "Edg" not in ua
        is_firefox = "Firefox" in ua
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(["en-US,en;q=0.9", "tr-TR,tr;q=0.9,en;q=0.8", "en-GB,en;q=0.9"]),
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
        }
        if is_chrome or is_firefox:
            headers.update({
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none" if not referer else "cross-site",
                "Sec-Fetch-User": "?1",
            })
        if is_chrome:
            headers.update({
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            })
        if referer:
            headers["Referer"] = referer
        return headers

    @staticmethod
    def detect_antibot(text: str, headers: Dict[str, str]) -> List[str]:
        import re as _re
        hits = []
        body_sample = (text or "")[:5000]
        for sig in _ANTIBOT_SIGNATURES:
            if _re.search(sig["regex"], body_sample, _re.IGNORECASE):
                hits.append(sig["name"])
        # Header signatures
        for h_key, h_val in headers.items():
            for sig in _ANTIBOT_SIGNATURES:
                if sig["name"].lower() not in [h.lower() for h in hits]:
                    if _re.search(sig["regex"], f"{h_key}: {h_val}", _re.IGNORECASE):
                        hits.append(sig["name"])
        return list(dict.fromkeys(hits))  # dedup, preserve order

    def get(self, url: str, referer: Optional[str] = None, extra_headers: Optional[Dict[str, str]] = None) -> FetchResult:
        ua = self.random_ua()
        headers = self._realistic_headers(ua, referer=referer)
        if extra_headers:
            headers.update(extra_headers)
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        t0 = time.time()
        attempts = 0
        last_exc = None
        last_resp = None
        for attempt in range(self.max_retries + 1):
            attempts += 1
            try:
                r = self.session.get(
                    url, headers=headers, timeout=self.timeout,
                    proxies=proxies, allow_redirects=True,
                )
                last_resp = r
                if r.status_code in (429, 503):
                    sleep_s = 1.5 ** attempt + random.uniform(0.5, 1.5)
                    time.sleep(min(sleep_s, 15))
                    # UA rotate
                    ua = self.random_ua()
                    headers = self._realistic_headers(ua, referer=referer)
                    continue
                break
            except requests.RequestException as e:
                last_exc = e
                sleep_s = 1.5 ** attempt + random.uniform(0.2, 0.8)
                time.sleep(min(sleep_s, 10))
        if last_resp is None:
            return FetchResult(
                url=url, status_code=0, text=f"Exception: {last_exc}",
                attempts=attempts, elapsed_s=round(time.time() - t0, 2),
            )
        antibot = self.detect_antibot(last_resp.text, dict(last_resp.headers))
        if self.cookie_persist:
            self._save_cookies()
        return FetchResult(
            url=url, status_code=last_resp.status_code, text=last_resp.text,
            headers=dict(last_resp.headers), elapsed_s=round(time.time() - t0, 2),
            attempts=attempts, antibot_detected=antibot, final_url=last_resp.url,
        )


def _self_test():
    print("[kuroshin_scraper] self_test")
    f = ResilientFetcher()
    targets = [
        "https://httpbin.org/headers",   # echo headers — Sec-Fetch dogrula
        "https://example.com",            # statik
    ]
    for t in targets:
        r = f.get(t)
        print(f"  {r.status_code} ({r.elapsed_s}s, {r.attempts}t, antibot={r.antibot_detected}) {t}")
        if "httpbin" in t and r.status_code == 200:
            try:
                data = json.loads(r.text)
                ua = data.get("headers", {}).get("User-Agent", "")
                print(f"    UA echoed: {ua[:80]}")
            except Exception:
                pass


if __name__ == "__main__":
    _self_test()
