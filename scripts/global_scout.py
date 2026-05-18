"""
Kuroshin Küresel Keşif v2.1 — GERÇEK KAYNAKLAR
================================================
Hükümdar Emri (26 Nis 2026): DDGS çöplüğü tasfiye edildi.
Kaynaklar: Habr RSS, Gitee API, Codeby forum, arXiv, HF Datasets, HackerNews,
           Qiita API, Zenn RSS, Papers with Code, Exploit-DB RSS
IP eşikleri sertleştirildi. Çeviri: PeCa 1B (fallback: deep-translator).
Her bulgu EYLEM satırıyla sunulur.

Zamanlama: Her gün 20:00 — catchup aktif.
"""

import json
import os
import re
import time
import traceback
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path("/mnt/c/Kuroshin/.env"))

# ── CONFIG ────────────────────────────────────────────────
LAST_SCAN_FILE   = Path("/mnt/c/Kuroshin/memory/scout_last_scan.json")
REPORTS_DIR      = Path("/mnt/c/Kuroshin/memory/scout_reports")
LOG_PATH         = Path("/mnt/c/Kuroshin/logs/global_scout.log")
LLAMA_URL        = "http://127.0.0.1:8080/v1/chat/completions"
LLAMA_MODEL      = "mlabonne_Qwen3-8B-abliterated-Q5_K_M.gguf"
PECA_URL         = "http://127.0.0.1:8080/v1/chat/completions"   # PeCa 1B varsa farklı port
PECA_MODEL       = "peca-llama32-1b-merged-q4_k_m.gguf"
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT    = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
SCAN_HOUR        = 20
MAX_CATCHUP_DAYS = 3
HEADERS          = {"User-Agent": "Kuroshin/2.0 (+https://kuroshin.local)"}
MODELS_DIR       = Path("/root/kuroshin/models")

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(Path(__file__).parent))
from kuroshin_utils import setup_logger as _setup_logger
_gs_logger = _setup_logger("global_scout", LOG_PATH)

# ── KAYNAK GÜVENİLİRLİK AĞIRLIKLARI ─────────────────────
SOURCE_RELIABILITY = {
    "arxiv":         0.98,
    "paperswithcode": 0.88,
    "gitee":         0.70,
    "habr":          0.65,
    "codeby":        0.55,
    "qiita":         0.55,
    "hf_datasets":   0.85,
    "hackernews":    0.45,
    "qiita":         0.55,
    "zenn":          0.55,
    "paperswithcode": 0.88,
    "exploitdb":     0.90,
    "ddgs":          0.15,   # düşürüldü — artık fallback
}

# ── KATEGORİ TANIMI (v2.0 — sertleştirilmiş eşikler) ─────
CATEGORIES = {
    "dataset": {
        "icon": "📦", "label": "VERİ SETLERİ",
        "queries_arxiv": [
            "instruction tuning dataset synthetic data llm fine-tuning",
            "preference dataset DPO RLHF alignment 2026",
        ],
        "ip_bonus": {"has_dataset": 15, "uncensored": 10},
        "thresholds": {"acil": 55, "test": 38, "izle": 22},
    },
    "uncensored": {
        "icon": "🕶️", "label": "SANSÜRSÜZ & KISITLI",
        "queries_arxiv": [
            "uncensored model alignment bypass jailbreak llm no guardrails",
            "unfiltered weights local inference safety removal",
        ],
        "ip_bonus": {"uncensored": 15},
        "thresholds": {"acil": 50, "test": 33, "izle": 18},
    },
    "algorithm": {
        "icon": "🧠", "label": "ALGORİTMA & MİMARİ",
        "queries_arxiv": [
            "bitnet 1-bit llm inference cpu optimization sparse attention",
            "speculative decoding draft model kv cache pruning 2026",
        ],
        "ip_bonus": {},
        "thresholds": {"acil": 45, "test": 28, "izle": 15},
    },
    "security": {
        "icon": "🛡️", "label": "GÜVENLİK & SIZMA",
        "queries_arxiv": [
            "new fuzzer security tool vulnerability penetration testing",
            "red team adversarial attack language model exploit 2026",
        ],
        "ip_bonus": {},
        "thresholds": {"acil": 55, "test": 38, "izle": 20},
    },
    "os_infra": {
        "icon": "⚙️", "label": "İŞLETİM SİSTEMİ & ALTYAPI",
        "queries_arxiv": [
            "rust unikernel operating system microkernel embedded hypervisor",
            "wsl2 linux kernel optimization llm inference container",
        ],
        "ip_bonus": {},
        "thresholds": {"acil": 45, "test": 28, "izle": 15},
    },
}

# ── LOGGING ───────────────────────────────────────────────
def _log(msg: str):
    _gs_logger.info(msg)

# ── LAST SCAN / RAPOR NO ──────────────────────────────────
def load_last_scan() -> dict:
    if LAST_SCAN_FILE.exists():
        try:
            return json.loads(LAST_SCAN_FILE.read_text())
        except Exception as _e:
            _log(f"[SCOUT] HATA: {_e}")
    return {}

def save_last_scan(data: dict):
    LAST_SCAN_FILE.write_text(json.dumps(data, indent=2))

def get_next_report_number() -> int:
    scans = load_last_scan()
    n = scans.get("report_count", 0) + 1
    scans["report_count"] = n
    save_last_scan(scans)
    return n

# ── TELEGRAM ──────────────────────────────────────────────
def send_telegram(text: str):
    MAX = 4000
    chunks = [text[i:i+MAX] for i in range(0, max(len(text), 1), MAX)]
    for chunk in chunks:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT, "text": chunk, "parse_mode": "HTML"},
                timeout=15,
            )
            time.sleep(0.5)
        except Exception as e:
            _log(f"Telegram hata: {e}")


# ── HATA BİLDİRİMİ ───────────────────────────────────────
def send_alert(source: str, reason: str, detail: str = ""):
    """Kaynak zaman aşımı, düşük kalite veya disk dolu uyarıları."""
    parts = [
        "⚠️ <b>Küresel Keşif Uyarısı</b>",
        f"Kaynak: <code>{source}</code>",
        f"Neden: {reason}",
    ]
    if detail:
        parts.append(f"<code>{detail[:200]}</code>")
    send_telegram("\n".join(parts))
    _log(f"ALERT [{source}]: {reason}")

def _check_disk():
    """Disk doluluk uyarısı — /root 90% üzerindeyse bildir."""
    import shutil
    try:
        usage = shutil.disk_usage("/root")
        pct = usage.used / usage.total * 100
        if pct > 90:
            send_alert(
                "disk",
                f"Disk %{pct:.1f} dolu!",
                f"Kullanılan: {usage.used//1024**3} GB / {usage.total//1024**3} GB",
            )
    except Exception as _e:
        _log(f"[SCOUT] HATA: {_e}")


# ── BÖLGESEL ETİKET ───────────────────────────────────────
def detect_region(url: str) -> str:
    u = url.lower()
    if any(x in u for x in ["habr.", "codeby.", "xakep.", "habr.com"]):
        return "🇷🇺"
    if any(x in u for x in ["gitee.", "csdn.", "juejin.", "zhihu.", "gitee.com"]):
        return "🇨🇳"
    if any(x in u for x in ["qiita.", "zenn.", "qiita.com"]):
        return "🇯🇵"
    return "🌐"

# ╔══════════════════════════════════════════════════════════╗
# ║  KAYNAKLAR                                               ║
# ╚══════════════════════════════════════════════════════════╝

def fetch_habr_rss(hours: int = 36) -> list[dict]:
    """Habr RSS — son 36 saatin Rusça teknik makaleleri."""
    results = []
    try:
        feed = feedparser.parse(
            "https://habr.com/ru/rss/articles/all/",
            request_headers=HEADERS,
        )
        cutoff = datetime.now() - timedelta(hours=hours)
        for entry in feed.entries:
            try:
                pub = datetime(*entry.published_parsed[:6])
            except Exception:
                pub = datetime.now() - timedelta(hours=hours - 1)
            if pub < cutoff:
                continue
            results.append({
                "title":       entry.get("title", ""),
                "url":         entry.get("link", ""),
                "description": BeautifulSoup(
                    entry.get("summary", ""), "html.parser"
                ).get_text()[:200],
                "source":      "habr",
                "date":        pub.isoformat(),
            })
        _log(f"Habr RSS: {len(results)} makale")
    except Exception as e:
        _log(f"Habr hatası: {e}")
    return results


def fetch_gitee_trending() -> list[dict]:
    """Gitee v5 search API — AI/LLM/Security repo'lar.
    Not: WSL2/Türkiye'den erişim kısıtlı olabilir → graceful fallback."""
    results = []
    search_terms = ["llm gguf", "security exploit", "quantization inference"]
    for term in search_terms:
        try:
            resp = requests.get(
                "https://gitee.com/api/v5/repos/search",
                params={"q": term, "sort": "stars_count", "order": "desc",
                        "limit": 5, "type": "public"},
                headers=HEADERS, timeout=15,
            )
            if resp.status_code != 200:
                continue
            for repo in resp.json()[:5]:
                results.append({
                    "title":       repo.get("full_name", ""),
                    "url":         repo.get("html_url", ""),
                    "description": (repo.get("description") or "")[:200],
                    "stars":       repo.get("stargazers_count", 0),
                    "source":      "gitee",
                    "language":    repo.get("language", ""),
                })
        except Exception as _e:
            _log(f"[SCOUT] HATA: {_e}")
        time.sleep(1)
    _log(f"Gitee: {len(results)} repo")
    return results


def fetch_codeby_recent() -> list[dict]:
    """Codeby.net forum — Rusça güvenlik thread başlıkları (HTML scrape)."""
    results = []
    try:
        resp = requests.get(
            "https://codeby.net/forums/",
            headers=HEADERS, timeout=25,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        # /threads/ URL'si içeren tüm linkleri topla
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/threads/" not in href:
                continue
            url = href if href.startswith("http") else "https://codeby.net" + href
            # Pozisyon anchor'larını temizle
            url = url.split("#")[0].split("?")[0]
            if url in seen:
                continue
            seen.add(url)
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            results.append({"title": title, "url": url, "source": "codeby", "description": ""})
            if len(results) >= 12:
                break
        _log(f"Codeby: {len(results)} başlık")
    except Exception as e:
        _log(f"Codeby hatası: {e}")
    return results


def fetch_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """arXiv API — son 7 gündeki makaleler."""
    try:
        resp = requests.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": query,
                "sortBy":       "submittedDate",
                "sortOrder":    "descending",
                "max_results":  max_results,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return []
        entries = re.findall(r"<entry>(.*?)</entry>", resp.text, re.DOTALL)
        cutoff = datetime.utcnow() - timedelta(days=7)
        results = []
        for entry in entries:
            title = re.search(r"<title>(.*?)</title>",   entry, re.DOTALL)
            link  = re.search(r"<id>(.*?)</id>",         entry, re.DOTALL)
            summ  = re.search(r"<summary>(.*?)</summary>",entry, re.DOTALL)
            pub   = re.search(r"<published>(.*?)</published>", entry, re.DOTALL)
            if not title or not link:
                continue
            pub_str = pub.group(1).strip() if pub else ""
            try:
                if datetime.fromisoformat(pub_str[:10]) < cutoff:
                    continue
            except Exception as _e:
                _log(f"[SCOUT] HATA: {_e}")
            results.append({
                "title":       title.group(1).strip().replace("\n", " "),
                "url":         link.group(1).strip(),
                "description": (summ.group(1).strip().replace("\n", " ")[:300] if summ else ""),
                "source":      "arxiv",
                "date":        pub_str[:10],
            })
        return results
    except Exception as e:
        _log(f"arXiv hata ({query[:50]}): {e}")
        return []


def fetch_hf_datasets(search: str = "", max_results: int = 8) -> list[dict]:
    """HuggingFace Datasets API."""
    try:
        params = {"sort": "createdAt", "direction": "-1", "limit": max_results}
        if search:
            params["search"] = search
        resp = requests.get("https://huggingface.co/api/datasets", params=params, timeout=30)
        if resp.status_code != 200:
            return []
        cutoff = datetime.utcnow() - timedelta(days=7)
        results = []
        for d in resp.json():
            try:
                dt = datetime.fromisoformat(
                    d.get("createdAt", "").replace("Z", "+00:00")
                ).replace(tzinfo=None)
                if dt < cutoff:
                    continue
            except Exception as _e:
                _log(f"[SCOUT] HATA: {_e}")
            results.append({
                "title":       d.get("id", ""),
                "url":         f"https://huggingface.co/datasets/{d.get('id','')}",
                "description": f"Downloads: {d.get('downloads',0)} | Likes: {d.get('likes',0)}",
                "downloads":   d.get("downloads", 0),
                "likes":       d.get("likes", 0),
                "tags":        d.get("tags", []),
                "source":      "hf_datasets",
            })
        return results
    except Exception as e:
        _log(f"HF Datasets hata: {e}")
        return []


def fetch_hn_stories(query: str, max_results: int = 5) -> list[dict]:
    """Algolia HN search."""
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "tags": "story", "hitsPerPage": max_results},
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        results = []
        for h in resp.json().get("hits", []):
            results.append({
                "title":       h.get("title", ""),
                "url":         h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}",
                "description": h.get("story_text", "")[:200],
                "points":      h.get("points", 0),
                "comments":    h.get("num_comments", 0),
                "source":      "hackernews",
            })
        return results
    except Exception as e:
        _log(f"HN hata: {e}")
        return []

def fetch_qiita(tag: str = "llm", max_results: int = 8) -> list[dict]:
    """Qiita API v2 — Japonca teknik makaleler (LLM, AI, Security)."""
    results = []
    try:
        resp = requests.get(
            "https://qiita.com/api/v2/items",
            params={"query": f"tag:{tag}", "per_page": max_results, "page": 1},
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=20,
        )
        if resp.status_code != 200:
            _log(f"Qiita HTTP {resp.status_code}")
            return []
        cutoff = datetime.utcnow() - timedelta(days=7)
        for item in resp.json():
            try:
                pub = datetime.fromisoformat(
                    item.get("created_at", "")[:19]
                )
                if pub < cutoff:
                    continue
            except Exception as _e:
                _log(f"[SCOUT] HATA: {_e}")
            tags = [t["name"] for t in item.get("tags", [])]
            results.append({
                "title":       item.get("title", ""),
                "url":         item.get("url", ""),
                "description": (item.get("body") or "")[:200],
                "likes":       item.get("likes_count", 0),
                "tags":        tags,
                "source":      "qiita",
                "date":        item.get("created_at", "")[:10],
            })
        _log(f"Qiita [{tag}]: {len(results)} makale")
    except Exception as e:
        _log(f"Qiita hata: {e}")
    return results


def fetch_zenn(topic: str = "llm") -> list[dict]:
    """Zenn RSS — Japonca LLM/AI içerik."""
    results = []
    url = f"https://zenn.dev/topics/{topic}/feed"
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        cutoff = datetime.utcnow() - timedelta(days=7)
        for entry in feed.entries:
            try:
                pub = datetime(*entry.published_parsed[:6])
                if pub < cutoff:
                    continue
            except Exception:
                pub = datetime.utcnow()
            results.append({
                "title":       entry.get("title", ""),
                "url":         entry.get("link", ""),
                "description": BeautifulSoup(
                    entry.get("summary", ""), "html.parser"
                ).get_text()[:200],
                "source":      "zenn",
                "date":        pub.isoformat()[:10],
            })
        _log(f"Zenn [{topic}]: {len(results)} makale")
    except Exception as e:
        _log(f"Zenn hata: {e}")
    return results


def fetch_paperswithcode(query: str = "", max_results: int = 8) -> list[dict]:
    """Papers with Code API — son 7 günün ML makaleleri (kod içeren)."""
    results = []
    try:
        params: dict = {"ordering": "-arxiv_id", "has_github": "true", "items_per_page": max_results}
        if query:
            params["q"] = query
        resp = requests.get(
            "https://paperswithcode.com/api/v1/papers/",
            params=params,
            headers=HEADERS,
            timeout=25,
        )
        if resp.status_code != 200:
            _log(f"PwC HTTP {resp.status_code}")
            return []
        if resp.text.strip().startswith("<"):
            _log("PwC: HTML yanıtı alındı (Cloudflare blok) — atlandı")
            return []
        for p in resp.json().get("results", []):
            results.append({
                "title":       p.get("title", ""),
                "url":         p.get("url_abs", "") or p.get("url_pdf", ""),
                "description": (p.get("abstract") or "")[:250],
                "stars":       p.get("github_stars") or 0,
                "source":      "paperswithcode",
                "date":        (p.get("published") or "")[:10],
            })
        _log(f"PwC [{query or 'latest'}]: {len(results)} makale")
    except Exception as e:
        _log(f"PwC hata: {e}")
    return results


def fetch_exploitdb_rss(max_items: int = 15) -> list[dict]:
    """Exploit-DB RSS — son açıklanan exploit'ler."""
    results = []
    try:
        feed = feedparser.parse(
            "https://www.exploit-db.com/rss.xml",
            request_headers=HEADERS,
        )
        cutoff = datetime.utcnow() - timedelta(days=7)
        for entry in feed.entries[:max_items]:
            try:
                pub = datetime(*entry.published_parsed[:6])
                if pub < cutoff:
                    continue
            except Exception:
                pub = datetime.utcnow()
            desc = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:200]
            results.append({
                "title":       entry.get("title", ""),
                "url":         entry.get("link", ""),
                "description": desc,
                "source":      "exploitdb",
                "date":        pub.isoformat()[:10],
            })
        _log(f"Exploit-DB: {len(results)} exploit")
    except Exception as e:
        _log(f"Exploit-DB hata: {e}")
    return results


# ╔══════════════════════════════════════════════════════════╗
# ║  IP SKORLAMA v2 (sertleştirilmiş ağırlıklar)            ║
# ╚══════════════════════════════════════════════════════════╝

KW_WEIGHTS = {
    # GGUF / llama.cpp ekosistemi
    "gguf": 9, "llama.cpp": 9, "quantiz": 7, "q4_k": 8, "q8": 5,
    "inference": 5, "local llm": 7, "local model": 6,
    # Sansürsüz / bypass
    "uncensored": 14, "no guardrail": 14, "bypass": 9, "unfiltered": 12,
    "jailbreak": 10, "alignment bypass": 12,
    # Veri seti
    "dataset": 6, "instruction": 7, "fine-tun": 8, "synthetic": 7,
    "dpo": 8, "rlhf": 7, "preference": 6,
    # Güvenlik
    "exploit": 9, "cve": 9, "fuzzer": 8, "pentest": 7,
    "nuclei": 7, "poc": 8, "zero-day": 10, "rce": 10,
    # Algoritma
    "bitnet": 10, "1-bit": 9, "speculative": 7, "mamba": 8,
    "pruning": 6, "kv cache": 7, "flash attention": 6,
    # Donanım uyumu
    "8gb": 7, "4bit": 7, "vram": 6, "rtx": 5, "laptop": 4,
    # Rust / OS
    "rust": 5, "unikernel": 8, "microkernel": 8, "hypervisor": 7,
}

def ip_score_v2(item: dict, category: str) -> int:
    text = (
        item.get("title", "") + " " +
        item.get("description", "") + " " +
        " ".join(item.get("tags", []))
    ).lower()

    score = 0
    for kw, pts in KW_WEIGHTS.items():
        if kw in text:
            score += pts

    # Kategori bonusu
    bonuses = CATEGORIES.get(category, {}).get("ip_bonus", {})
    if "has_dataset" in bonuses and "dataset" in text:
        score += bonuses["has_dataset"]
    if "uncensored" in bonuses and any(w in text for w in ["uncensored", "unfiltered", "jailbreak"]):
        score += bonuses["uncensored"]

    # Popülerlik bonusu
    pop = (
        item.get("points", 0) or
        item.get("likes", 0) or
        item.get("stars", 0) or
        (item.get("downloads", 0) // 500)
    )
    if pop > 1000: score += 12
    elif pop > 200: score += 8
    elif pop > 50:  score += 5
    elif pop > 10:  score += 3

    # Kaynak güvenilirlik ağırlığı
    reliability = SOURCE_RELIABILITY.get(item.get("source", ""), 0.3)
    return int(score * reliability)


def classify_item(score: int, cat: str) -> str | None:
    thr = CATEGORIES[cat]["thresholds"]
    if score >= thr["acil"]: return "🔴 ACİL"
    if score >= thr["test"]:  return "🟡 TEST"
    if score >= thr["izle"]:  return "🔵 İZLE"
    return None

# ╔══════════════════════════════════════════════════════════╗
# ║  EYLEM ÜRETECİ                                           ║
# ╚══════════════════════════════════════════════════════════╝

def action_for(item: dict, cat: str) -> str:
    url   = item.get("url", "")
    title = item.get("title", "")
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", title[:30])

    if "github.com" in url or "gitee.com" in url:
        return f"git clone {url} /root/kuroshin/experiments/{safe_name}"
    elif "arxiv.org" in url:
        return f"Makaleyi kaydet → /root/kuroshin/memory/research/{safe_name}.md"
    elif "huggingface.co/datasets" in url:
        ds_id = title.replace("/", "__")[:25]
        return f"hf download {title} --local-dir /root/kuroshin/datasets/{ds_id} --repo-type dataset"
    elif "huggingface.co" in url and "/" in title:
        short = title.split("/")[-1][:20]
        return f"hf download {title} --local-dir {MODELS_DIR}/{short} --include '*.gguf'"
    elif "codeby.net" in url or "habr.com" in url:
        return "İzole ortamda incele — doğrudan çalıştırma."
    else:
        return "🔗 Manuel inceleme — içeriği değerlendir."

# ╔══════════════════════════════════════════════════════════╗
# ║  ÇEVİRİ (PeCa 1B önce, fallback: deep-translator)       ║
# ╚══════════════════════════════════════════════════════════╝

def _translate_peca(text: str) -> str:
    """PeCa 1B ile EN→TR çeviri — llama-server üzerinde."""
    prompt = (
        f"[INST] Translate this text to Turkish. Keep technical terms (like GGUF, CVE, "
        f"LLM, fuzzer, inference) in original form. Only output the translation, nothing else:\n"
        f"{text[:400]} [/INST]"
    )
    try:
        resp = requests.post(PECA_URL, json={
            "model":       PECA_MODEL,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  200,
            "temperature": 0.1,
        }, timeout=30)
        if resp.status_code == 200:
            out = resp.json()["choices"][0]["message"]["content"].strip()
            if out and len(out) > 5:
                return out
    except Exception as _e:
        _log(f"[SCOUT] HATA: {_e}")
    return ""


def translate_tr(text: str) -> str:
    """PeCa 1B → fallback deep-translator → fallback orijinal."""
    if not text or len(text) < 5:
        return text

    # PeCa 1B dene
    result = _translate_peca(text)
    if result:
        return result

    # deep-translator fallback
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target="tr").translate(text[:500]) or text
    except Exception:
        return text

# ╔══════════════════════════════════════════════════════════╗
# ║  ANA TARAMA                                              ║
# ╚══════════════════════════════════════════════════════════╝

def run_scout() -> str | None:
    scan_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    _log(f"=== KÜRESEL KEŞİF v2.1 BAŞLIYOR: {scan_time} ===")
    send_telegram(
        f"🧭 <b>Küresel Keşif v2.1 Başladı</b>\n"
        f"📅 {scan_time}\n"
        f"Kaynaklar: Habr RSS · Gitee · Codeby · arXiv · HF Datasets · HN\n"
        f"⏳ Sonuç ~5-8 dakika içinde gelecek."
    )
    t_start = time.time()
    _check_disk()

    # category → scored items
    by_cat: dict[str, list[dict]] = {k: [] for k in CATEGORIES}
    total_raw = 0
    _progress_candidates = 0

    def _progress(step: int, label: str, found: int):
        """Her kaynak tamamlandığında Telegram'a kısa ilerleme mesajı."""
        filled = step * 10 // 10
        bar = "█" * step + "░" * (10 - step)
        pct = step * 10
        elapsed_s = int(time.time() - t_start)
        send_telegram(
            f"📡 <b>Keşif İlerliyor</b> [{bar}] %{pct}\n"
            f"✅ {label} → {found} aday | ⏱️ {elapsed_s}s"
        )

    # ── 1. Habr RSS ──────────────────────────────────────
    _log("1/10 Habr RSS taranıyor...")
    habr_items = fetch_habr_rss(hours=36)
    if not habr_items:
        send_alert("habr", "RSS boş veya zaman aşımı")
    _step_found = 0
    for item in habr_items:
        for cat in CATEGORIES:
            sc = ip_score_v2(item, cat)
            if sc >= CATEGORIES[cat]["thresholds"]["izle"]:
                by_cat[cat].append({**item, "score": sc})
                _step_found += 1
        total_raw += 1
    _progress_candidates += _step_found
    _progress(1, f"Habr RSS ({len(habr_items)} makale)", _progress_candidates)

    # ── 2. Gitee ─────────────────────────────────────────
    _log("2/10 Gitee Trending taranıyor...")
    _step_found = 0
    for item in fetch_gitee_trending():
        for cat in CATEGORIES:
            sc = ip_score_v2(item, cat)
            if sc >= CATEGORIES[cat]["thresholds"]["izle"]:
                by_cat[cat].append({**item, "score": sc})
                _step_found += 1
        total_raw += 1
    _progress_candidates += _step_found
    _progress(2, f"Gitee Trending", _progress_candidates)

    # ── 3. Codeby (Güvenlik kategorisi) ──────────────────
    _log("3/10 Codeby forum taranıyor...")
    _step_found = 0
    for item in fetch_codeby_recent():
        sc = ip_score_v2(item, "security")
        if sc >= CATEGORIES["security"]["thresholds"]["izle"]:
            by_cat["security"].append({**item, "score": sc})
            _step_found += 1
        total_raw += 1
    _progress_candidates += _step_found
    _progress(3, f"Codeby Forum", _progress_candidates)

    # ── 4. arXiv ─────────────────────────────────────────
    _log("4/10 arXiv taranıyor...")
    _step_found = 0
    for cat, cat_info in CATEGORIES.items():
        for q in cat_info["queries_arxiv"][:2]:
            items = fetch_arxiv(q, max_results=5)
            for it in items:
                # arXiv'den gelen makaleler: "dataset" sorgusuyla gelse bile
                # başlıkta/açıklamada "dataset" geçmiyorsa algorithm kategorisine yönlendir
                eff_cat = cat
                if cat == "dataset" and "dataset" not in (it.get("title","") + it.get("description","")).lower():
                    eff_cat = "algorithm"
                sc = ip_score_v2(it, eff_cat)
                if sc >= CATEGORIES[eff_cat]["thresholds"]["izle"]:
                    by_cat[eff_cat].append({**it, "score": sc})
                    _step_found += 1
            total_raw += len(items)
            time.sleep(1)
    _progress_candidates += _step_found
    _progress(4, f"arXiv", _progress_candidates)

    # ── 5. HF Datasets ───────────────────────────────────
    _log("5/10 HF Datasets taranıyor...")
    _step_found = 0
    for kw in ["instruction", "uncensored", "synthetic", "dpo"]:
        for it in fetch_hf_datasets(kw, max_results=6):
            sc = ip_score_v2(it, "dataset")
            if sc >= CATEGORIES["dataset"]["thresholds"]["izle"]:
                by_cat["dataset"].append({**it, "score": sc})
                _step_found += 1
        total_raw += 6
        time.sleep(0.8)
    _progress_candidates += _step_found
    _progress(5, f"HF Datasets", _progress_candidates)

    # ── 6. Hacker News ───────────────────────────────────────────────
    _log("6/10 Hacker News taranıyor...")
    hn_map = {
        "algorithm": "llm inference optimization gguf local 2026",
        "security":  "exploit fuzzer vulnerability pentest 2026",
    }
    _step_found = 0
    for cat, q in hn_map.items():
        for it in fetch_hn_stories(q, max_results=5):
            sc = ip_score_v2(it, cat)
            if sc >= CATEGORIES[cat]["thresholds"]["izle"]:
                by_cat[cat].append({**it, "score": sc})
                _step_found += 1
        total_raw += 5
        time.sleep(0.5)
    _progress_candidates += _step_found
    _progress(6, f"Hacker News", _progress_candidates)

    # ── 7. Qiita ───────────────────────────────────────────────────
    _log("7/10 Qiita taranıyor...")
    qiita_map = {
        "algorithm": "llm",
        "security":  "security",
        "os_infra":  "rust",
    }
    _step_found = 0
    for cat, tag in qiita_map.items():
        for it in fetch_qiita(tag=tag, max_results=8):
            sc = ip_score_v2(it, cat)
            if sc >= CATEGORIES[cat]["thresholds"]["izle"]:
                by_cat[cat].append({**it, "score": sc})
                _step_found += 1
        total_raw += 8
        time.sleep(1)
    _progress_candidates += _step_found
    _progress(7, f"Qiita", _progress_candidates)

    # ── 8. Zenn ──────────────────────────────────────────────────────
    _log("8/10 Zenn RSS taranıyor...")
    zenn_map = {
        "algorithm": "llm",
        "dataset":   "machine-learning",
    }
    _step_found = 0
    for cat, topic in zenn_map.items():
        for it in fetch_zenn(topic=topic):
            sc = ip_score_v2(it, cat)
            if sc >= CATEGORIES[cat]["thresholds"]["izle"]:
                by_cat[cat].append({**it, "score": sc})
                _step_found += 1
        total_raw += 10
        time.sleep(1)
    _progress_candidates += _step_found
    _progress(8, "Zenn RSS", _progress_candidates)

    # ── 9. Papers with Code ──────────────────────────────────────────────
    _log("9/10 Papers with Code taranıyor...")
    pwc_map = {
        "algorithm":  "llm inference quantization",
        "security":   "adversarial attack llm jailbreak",
        "dataset":    "instruction tuning dataset",
        "uncensored": "safety alignment bypass",
    }
    _step_found = 0
    for cat, q in pwc_map.items():
        for it in fetch_paperswithcode(query=q, max_results=5):
            sc = ip_score_v2(it, cat)
            if sc >= CATEGORIES[cat]["thresholds"]["izle"]:
                by_cat[cat].append({**it, "score": sc})
                _step_found += 1
        total_raw += 5
        time.sleep(1)
    _progress_candidates += _step_found
    _progress(9, "Papers with Code", _progress_candidates)

    # ── 10. Exploit-DB RSS ───────────────────────────────────────────────
    _log("10/10 Exploit-DB RSS taranıyor...")
    exdb_items = fetch_exploitdb_rss(max_items=15)
    if not exdb_items:
        send_alert("exploitdb", "RSS boş veya zaman aşımı")
    _step_found = 0
    for it in exdb_items:
        sc = ip_score_v2(it, "security")
        if sc >= CATEGORIES["security"]["thresholds"]["izle"]:
            by_cat["security"].append({**it, "score": sc})
            _step_found += 1
    total_raw += 15
    _progress_candidates += _step_found
    _progress(10, "Exploit-DB", _progress_candidates)

    # ── Dedup + top-3 per category ───────────────────────
    seen_urls: set[str] = set()
    for cat in by_cat:
        unique = []
        for it in sorted(by_cat[cat], key=lambda x: x.get("score", 0), reverse=True):
            u = it.get("url", "")
            if u and u in seen_urls:
                continue
            seen_urls.add(u)
            unique.append(it)
        by_cat[cat] = unique[:3]

    total_candidates = sum(len(v) for v in by_cat.values())
    elapsed = int(time.time() - t_start)
    _log(f"Ham: {total_raw} | Aday: {total_candidates} | Süre: {elapsed}s")

    if total_candidates == 0:
        _log("Kayda değer bulgu yok. Rapor atlandı.")
        send_telegram(
            f"🧭 <b>Küresel Keşif Tamamlandı</b>\n"
            f"📅 {scan_time}\n"
            f"Taranan: {total_raw} kayıt\n"
            f"⚠️ Eşik altında: hiçbir bulgu raporlanmadı."
        )
        return None

    # ── Rapor üret ───────────────────────────────────────
    report_no = get_next_report_number()
    report = _format_report(by_cat, scan_time, report_no, total_raw, total_candidates, elapsed)

    # Kaydet
    report_file = REPORTS_DIR / f"scout_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    report_file.write_text(report, encoding="utf-8")
    _log(f"Rapor: {report_file.name}")

    # Telegram
    send_telegram(report)
    _log("Rapor Telegram'a gönderildi.")

    # Son tarama kaydet
    scans = load_last_scan()
    scans["last"]       = datetime.now().isoformat()
    scans["last_label"] = scan_time
    save_last_scan(scans)

    return report

# ╔══════════════════════════════════════════════════════════╗
# ║  RAPOR FORMATLAYICI                                       ║
# ╚══════════════════════════════════════════════════════════╝

def _format_report(
    by_cat: dict, scan_time: str, report_no: int,
    total_raw: int, total_candidates: int, elapsed_s: int
) -> str:
    parts = [
        "🧭 <b>KUROSHIN KÜRESEL KEŞİF İSTİHBARATI v2.0</b>",
        f"🌊 {scan_time} — Gün Batımı | #{report_no:03d}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Yönetici özeti
    cat_summary = [
        f"{CATEGORIES[c]['icon']} {len(v)}"
        for c, v in by_cat.items() if v
    ]
    if cat_summary:
        parts.append(
            f"📌 <b>YÖNETİCİ ÖZETİ</b>\n"
            f"Bugün {' | '.join(cat_summary)} bulgu. "
            f"Gerçek kaynaklar: Habr · Gitee · Codeby · arXiv · HF · HN."
        )
    parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Kategori bölümleri
    for cat_key, cat_info in CATEGORIES.items():
        items = by_cat.get(cat_key, [])
        if not items:
            continue

        parts.append(f"\n{cat_info['icon']} <b>{cat_info['label']}</b>")

        for item in items:
            sc     = item.get("score", 0)
            klas   = classify_item(sc, cat_key)
            if not klas:
                continue

            region = detect_region(item.get("url", ""))
            title  = item.get("title", "?")[:80]
            desc   = (item.get("description") or "")[:150]
            url    = item.get("url", "")
            src    = item.get("source", "?").upper()
            eylem  = action_for(item, cat_key)

            # Çeviri — başlık + özet
            title_tr = translate_tr(title)
            desc_tr  = translate_tr(desc) if desc else ""

            parts.append(
                f"\n{klas} (IP:{sc}) {region} [{src}]\n"
                f"│ <b>{title_tr[:80]}</b>\n"
                + (f"│ {desc_tr[:120]}\n" if desc_tr else "")
                + f"│ 🔗 {url}\n"
                f"│ ⚡ EYLEM: <code>{eylem}</code>"
            )

        parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # İstatistik
    parts += [
        "📊 <b>KEŞİF İSTATİSTİĞİ</b>",
        f"   Taranan: {total_raw} kayıt | Aday: {total_candidates} | Raporlanan: {sum(len(v) for v in by_cat.values())}",
        f"   Kaynaklar: " + " · ".join(sorted({"Habr", "Gitee", "Codeby", "arXiv", "HF", "HN", "Qiita", "Zenn", "PwC", "Exploit-DB"})),
        f"   🕒 Süre: {elapsed_s // 60} dk {elapsed_s % 60} sn",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "<i>🧭 Pusula her yönü gösterir, rotayı yalnızca İmparatorluk çizer.</i>",
        f"<i>⚔️ Kuroshin Küresel Keşif Birimi v2.0 — #{report_no:03d}</i>",
    ]

    return "\n".join(parts)

# ── ZAMANLAYICI ───────────────────────────────────────────
def should_scan_now() -> bool:
    now   = datetime.now()
    scans = load_last_scan()
    last  = scans.get("last")
    if not last:
        return True
    try:
        elapsed_h = (now - datetime.fromisoformat(last)).total_seconds() / 3600
        if elapsed_h < 20:
            return False
    except Exception:
        return True
    return abs(now.hour - SCAN_HOUR) <= 1

# ── CATCHUP ───────────────────────────────────────────────
def check_catchup():
    """Kaçırılan tarama varsa bildir ve hemen başlat."""
    scans = load_last_scan()
    last  = scans.get("last")
    if not last:
        return False
    try:
        elapsed_h = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 3600
        if elapsed_h > 26:
            missed = int(elapsed_h / 24)
            send_telegram(
                f"🧭 <b>Küresel Keşif v2.1 Uyandı</b>\n"
                f"Son keşif: {last[:16]}\n"
                f"~{missed} gün bilgi birikti. Şimdi tarama yapıyorum...\n"
                f"Kaynaklar: Habr · Gitee · Codeby · arXiv · HF · HN · Qiita · Zenn · PwC · Exploit-DB"
            )
            return True  # catchup taraması gerekli
    except Exception as _e:
        _log(f"[SCOUT] HATA: {_e}")
    return False

# ── ANA DÖNGÜ ─────────────────────────────────────────────
PID_FILE = "/tmp/kuroshin_scout.pid"

def _acquire_lock():
    """Aynı anda sadece bir instance çalışsın."""
    import os, signal, sys
    if Path(PID_FILE).exists():
        try:
            old_pid = int(Path(PID_FILE).read_text().strip())
            os.kill(old_pid, 0)  # process hâlâ var mı?
            _log(f"Zaten çalışıyor (PID {old_pid}). Çıkılıyor.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            pass  # eski PID ölmüş, devam
    Path(PID_FILE).write_text(str(os.getpid()))

def _release_lock():
    try: Path(PID_FILE).unlink()
    except: pass


def main():
    import sys, os
    _acquire_lock()
    import atexit; atexit.register(_release_lock)
    daemon_mode = "--daemon" in sys.argv

    _log(f"🧭 Kuroshin Küresel Keşif v2.1 BAŞLADI ({'daemon' if daemon_mode else 'cron'})")
    _log(f"Tarama saati: {SCAN_HOUR:02d}:00 | IP eşikleri: sertleştirilmiş")

    if daemon_mode:
        _sf = Path("/tmp/kuroshin_scout.started")
        if not _sf.exists():
            _sf.touch()
            send_telegram(
                f"🧭 <b>Küresel Keşif v2.1 Daemon Başladı</b>\n"
                f"Kaynaklar: Habr · Gitee · Codeby · arXiv · HF · HN · Qiita · Zenn · PwC · Exploit-DB\n"
                f"⏰ Tarama saati: her gün {SCAN_HOUR:02d}:00"
            )

    needs_catchup = check_catchup()

    if daemon_mode:
        if needs_catchup or should_scan_now():
            _log("Tarama başlatılıyor (catchup veya planlı)...")
            try:
                run_scout()
            except Exception:
                _log(f"Tarama hatası: {traceback.format_exc()}")
        while True:
            try:
                time.sleep(1800)
                if should_scan_now():
                    _log("Planlı keşif taraması...")
                    run_scout()
                else:
                    _log(f"Keşif zamanı değil. Sonraki: {SCAN_HOUR:02d}:00")
            except KeyboardInterrupt:
                _log("Küresel Keşif durduruldu.")
                break
            except Exception:
                _log(f"Döngü hatası: {traceback.format_exc()}")
                time.sleep(60)
    else:
        # Cron modu: tek seferlik
        _log("Cron modu — tek seferlik tarama")
        try:
            run_scout()
        except Exception:
            _log(f"Tarama hatası: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
