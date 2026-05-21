"""
Kuroshin Hype Tarayıcı v1.1
============================
Sabah 09:00 ve akşam 21:00'da GitHub Trending + HuggingFace Daily tara.
MPC kapalıysa o tarih aralığındaki eksikleri telafi eder.
Sonuçları Gemma4 ile filtreler, Telegram'a rapor gönderir.

v1.1: Gemma4 auto-launch, GitHub domain filtresi, VRAM tahmini, HF eşik yükseltme.

Çalıştırma: python3 /mnt/c/Kuroshin/scripts/hype_scanner.py
"""

import json
import os
import re
import subprocess
import time
import requests
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path("/mnt/c/Kuroshin/.env"))

# ── CONFIG ────────────────────────────────────────────
LAST_SCAN_FILE  = Path("/mnt/c/Kuroshin/memory/hype_last_scan.json")
REPORTS_DIR     = Path("/mnt/c/Kuroshin/memory/hype_reports")
LOG_PATH        = Path("/mnt/c/Kuroshin/logs/hype_scanner.log")
LLAMA_URL       = "http://127.0.0.1:8080/v1/chat/completions"
LLAMA_HEALTH    = "http://127.0.0.1:8080/health"
_STATE_FILE     = Path("/mnt/c/Kuroshin/memory/active_model.json")

def _load_active_model_info() -> tuple[str, str, int, float, float]:
    """Returns (name, path, context_size, size_gb, tok_s)"""
    try:
        if _STATE_FILE.exists():
            d = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            name = d.get("active_model", "")
            path = d.get("path", "")
            ctx = int(d.get("context_size", 16384) or 16384)
            size_gb = float(d.get("size_gb", 0.0) or 0.0)
            tok_s = float(d.get("tok_s", 0.0) or 0.0)
            if name and path:
                return name, path, ctx, size_gb, tok_s
    except Exception:
        pass
    fallback = "Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf"
    return fallback, f"/root/kuroshin/models/{fallback}", 16384, 18.7, 20.0

def _is_moe_model(model_name: str) -> bool:
    lower = model_name.lower()
    return any(tok in lower for tok in ("a3b", "-ax", "moe"))

LLAMA_MODEL, _LLAMA_MODEL_PATH, _LLAMA_CTX, _LLAMA_SIZE_GB, _LLAMA_TOK_S = _load_active_model_info()
LLAMA_BIN       = "/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
_moe_flags      = '-ot "exps=CPU"' if _is_moe_model(LLAMA_MODEL) else "--spec-type ngram-cache --draft-max 16 --draft-min 2 --draft-p-min 0.7"
LLAMA_CMD       = (
    f"nohup {LLAMA_BIN} -m {_LLAMA_MODEL_PATH} "
    f"--host 0.0.0.0 --port 8080 -ngl 99 -c {_LLAMA_CTX} -fa on "
    f"--mlock --no-mmap {_moe_flags} >> /root/kuroshin/logs/llama-server.log 2>&1 &"
)
COUNCIL_URL     = "http://127.0.0.1:9004/task"
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT   = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
SCAN_HOURS      = [9, 21]
MAX_CATCHUP_DAYS = 7
# HF GGUF filtre eşikleri
HF_MIN_DOWNLOADS = 5
HF_MIN_LIKES     = 0
HF_MAX_AGE_DAYS  = 30

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(Path(__file__).parent))
from kuroshin_utils import setup_logger as _setup_logger
_hs_logger = _setup_logger("hype_scanner", LOG_PATH)

# GitHub'dan kabul edilecek domain anahtar kelimeleri — bunların dışındakiler filtrelenir
GITHUB_DOMAIN_KEYWORDS = {
    "llm", "gguf", "llama", "inference", "quantiz", "quant", "4bit", "8bit",
    "agent", "agentic", "tool", "rag", "embed", "rerank", "vector", "chroma",
    "security", "exploit", "pentest", "fuzzer", "cve", "vuln",
    "rust", "kernel", "unikernel", "hypervisor", "wasm",
    "gemma", "qwen", "mistral", "phi", "smollm", "deepseek",
    "speculative", "kv cache", "flash", "lora", "finetune", "dataset",
    "local llm", "privacy", "offline", "smolagent",
}

KEYWORDS_IMPORTANT = [
    "gguf", "llama.cpp", "quantiz", "quant", "4bit", "q4", "q8",
    "gemma", "qwen", "llama", "mistral", "phi", "smollm",
    "rag", "rerank", "embed", "chromadb", "vector",
    "smolagents", "agent", "agentic", "tool use",
    "speculative", "draft", "kv cache", "flash attention",
    "lora", "adapter", "finetune", "dataset",
    "turbo", "fast", "speed", "throughput", "token/s",
    "local llm", "offline", "privacy",
]

# ── VRAM TAHMİN TABLOSU ───────────────────────────────
# (parametre_milyar, quant_tipi) → VRAM_GB
# Quant tipi: bpw (bit per weight) yaklaşımıyla hesaplanır
_QUANT_BPW = {
    "iq1": 1.5, "iq2": 2.5, "iq3": 3.5, "iq4": 4.5,
    "q2":  2.5, "q3":  3.5, "q4":  4.5, "q5":  5.5,
    "q6":  6.5, "q8":  8.5, "f16": 16.0, "bf16": 16.0,
}

def estimate_vram_from_name(model_name: str) -> str:
    """GGUF dosya/model adından parametre sayısı + quant parse edip VRAM tahmini döndür.

    Örnekler:
      Qwen2.5-7B-Q4_K_M.gguf  → ~4.3GB
      gemma-2-2b-it-Q8_0.gguf → ~2.4GB
    """
    name = model_name.lower()

    # Parametre sayısını bul (0.5b, 1b, 1.5b, 3b, 4b, 7b, 8b, 14b, 32b...)
    param_match = re.search(r'(\d+(?:\.\d+)?)\s*b(?:\b|illion|-)', name)
    if not param_match:
        return "?"
    params_b = float(param_match.group(1))

    # Quant türünü bul
    bpw = 4.5  # varsayılan Q4
    for quant_key, bits in sorted(_QUANT_BPW.items(), key=lambda x: -len(x[0])):
        if quant_key in name:
            bpw = bits
            break

    # VRAM ≈ params × bpw / 8 × 1.1 (overhead)
    vram_gb = round(params_b * bpw / 8 * 1.1, 1)

    # 8GB sınırına göre uyum işareti
    compat = "✅" if vram_gb <= 7.0 else ("⚠️" if vram_gb <= 8.0 else "❌")
    return f"{vram_gb}GB {compat}"

# ── LOGGING ───────────────────────────────────────────
def _log(msg: str):
    _hs_logger.info(msg)

# ── GEMMA4 HEALTHCHECK + AUTO-LAUNCH ──────────────────
def check_and_launch_gemma4(wait_secs: int = 45) -> bool:
    """Gemma4'ün ayakta olup olmadığını kontrol et; kapalıysa başlat.

    Returns True eğer Gemma4 kullanılabilir durumda, False ise analiz motoru çevrimdışı.
    """
    try:
        r = requests.get(LLAMA_HEALTH, timeout=5)
        if r.status_code == 200:
            _log("Gemma4 zaten aktif.")
            return True
    except Exception as _e:
        _log(f"[HYPE] HATA: {_e}")

    _log("Gemma4 kapalı — otomatik başlatma deneniyor...")
    try:
        subprocess.Popen(
            ["bash", "-c", LLAMA_CMD],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        _log(f"Gemma4 başlatma hatası: {e}")
        return False

    # Servis ayağa kalkana kadar bekle
    deadline = time.time() + wait_secs
    while time.time() < deadline:
        time.sleep(5)
        try:
            r = requests.get(LLAMA_HEALTH, timeout=4)
            if r.status_code == 200:
                _log(f"Gemma4 başarıyla başlatıldı ({int(time.time() - (deadline - wait_secs))}s).")
                return True
        except Exception as _e:
            _log(f"[HYPE] HATA: {_e}")

    _log("Gemma4 başlatılamadı — fallback analiz kullanılacak.")
    return False

# ── LAST SCAN YÖNETIMI ────────────────────────────────
def load_last_scan() -> dict:
    if LAST_SCAN_FILE.exists():
        try:
            return json.loads(LAST_SCAN_FILE.read_text())
        except Exception as _e:
            _log(f"[HYPE] HATA: {_e}")
    return {}

def save_last_scan(data: dict):
    LAST_SCAN_FILE.write_text(json.dumps(data, indent=2))

# ── TELEGRAM ──────────────────────────────────────────
def send_telegram(text: str):
    MAX = 4000
    chunks = [text[i:i+MAX] for i in range(0, max(len(text), 1), MAX)]
    for chunk in chunks:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT, "text": chunk, "parse_mode": "HTML"},
                timeout=15
            )
        except Exception as e:
            _log(f"Telegram hata: {e}")

# ── SCRAPING ─────────────────────────────────────────
def scrape_github_trending(period: str = "daily") -> list[dict]:
    """GitHub Trending sayfasını BeautifulSoup ile çek."""
    try:
        from bs4 import BeautifulSoup
        url = f"https://github.com/trending?since={period}&spoken_language_code=en"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            _log(f"GitHub HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        repos = []
        for article in soup.select("article.Box-row")[:25]:
            try:
                name_tag = article.select_one("h2 a")
                if not name_tag:
                    continue
                repo_path = name_tag.get("href", "").strip("/")
                desc_tag = article.select_one("p")
                desc = desc_tag.get_text(strip=True) if desc_tag else ""
                star_tag = article.select_one("a[href$='/stargazers']")
                stars_text = star_tag.get_text(strip=True).replace(",", "") if star_tag else "0"
                stars = 0
                try:
                    stars = int("".join(filter(str.isdigit, stars_text))) if stars_text else 0
                except Exception as _e:
                    _log(f"[HYPE] HATA: {_e}")
                star_today_tag = article.select_one("span.d-inline-block.float-sm-right")
                stars_today = star_today_tag.get_text(strip=True) if star_today_tag else ""
                lang_tag = article.select_one("[itemprop='programmingLanguage']")
                lang = lang_tag.get_text(strip=True) if lang_tag else ""
                # Domain filtresi: başlık/açıklama Kuroshin alanıyla eşleşmeli
                combined = f"{repo_path} {desc}".lower()
                if not any(kw in combined for kw in GITHUB_DOMAIN_KEYWORDS):
                    continue
                repos.append({
                    "source": "github",
                    "name": repo_path,
                    "url": f"https://github.com/{repo_path}",
                    "description": desc,
                    "stars": stars,
                    "stars_today": stars_today,
                    "language": lang,
                })
            except Exception:
                continue
        _log(f"GitHub Trending: {len(repos)} repo bulundu (domain filtresi sonrası)")
        return repos
    except ImportError:
        _log("BeautifulSoup yok — pip install beautifulsoup4")
        return []
    except Exception as e:
        _log(f"GitHub scrape hatası: {e}")
        return []


def scrape_hf_papers() -> list[dict]:
    """HuggingFace Daily Papers API'sinden son makaleleri çek."""
    try:
        url = "https://huggingface.co/api/daily_papers?limit=20"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            _log(f"HF Papers HTTP {resp.status_code}")
            return []
        data = resp.json()
        papers = []
        for item in data:
            paper = item.get("paper", {})
            papers.append({
                "source": "hf_paper",
                "name": paper.get("title", ""),
                "url": f"https://huggingface.co/papers/{paper.get('id', '')}",
                "description": paper.get("summary", "")[:300],
                "upvotes": item.get("totalUpvotes", 0),
                "published": paper.get("publishedAt", ""),
            })
        _log(f"HF Papers: {len(papers)} makale bulundu")
        return papers
    except Exception as e:
        _log(f"HF Papers hatası: {e}")
        return []


def scrape_hf_new_models() -> list[dict]:
    """HuggingFace'te son 30 günde yayınlanan GGUF modellerini ara.

    Filtreler (v1.1):
      - En az HF_MIN_DOWNLOADS indirme veya HF_MIN_LIKES beğeni
      - Son HF_MAX_AGE_DAYS gün içinde oluşturulmuş
      - Downloads:0 + Likes:0 olan sıfır etkileşimli modeller atlanır
    """
    try:
        url = "https://huggingface.co/api/models?filter=gguf&sort=createdAt&direction=-1&limit=40"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            _log(f"HF Models HTTP {resp.status_code}")
            return []
        data = resp.json()
        models = []
        cutoff = datetime.utcnow() - timedelta(days=HF_MAX_AGE_DAYS)
        for m in data:
            downloads = m.get("downloads", 0) or 0
            likes     = m.get("likes", 0) or 0
            # Sıfır etkileşimli modelleri atla
            if downloads < HF_MIN_DOWNLOADS and likes <= HF_MIN_LIKES:
                continue
            created = m.get("createdAt", "")
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
                if dt < cutoff:
                    continue
            except Exception as _e:
                _log(f"[HYPE] HATA: {_e}")
            model_id = m.get("modelId", "")
            vram_est = estimate_vram_from_name(model_id)
            models.append({
                "source":      "hf_model",
                "name":        model_id,
                "url":         f"https://huggingface.co/{model_id}",
                "description": f"Downloads: {downloads} | Likes: {likes} | VRAM: {vram_est}",
                "likes":       likes,
                "downloads":   downloads,
                "tags":        m.get("tags", []),
                "vram_est":    vram_est,
            })
        _log(f"HF GGUF Modeller: {len(models)} model (filtre: ≥{HF_MIN_DOWNLOADS} dl veya >{HF_MIN_LIKES} like)")
        return models
    except Exception as e:
        _log(f"HF Models hatası: {e}")
        return []

# ── KEYWORD FİLTRE ────────────────────────────────────
def keyword_score(item: dict) -> int:
    """Anahtar kelime eşleşmesine göre önem skoru."""
    text = f"{item.get('name','')} {item.get('description','')} {' '.join(item.get('tags',[]))}".lower()
    score = 0
    for kw in KEYWORDS_IMPORTANT:
        if kw in text:
            score += 1
    # Star/upvote bonusu
    stars = item.get("stars", 0) or item.get("upvotes", 0) or item.get("likes", 0)
    if stars > 1000:
        score += 3
    elif stars > 500:
        score += 2
    elif stars > 100:
        score += 1
    return score

# ── RAPOR NUMARASI ────────────────────────────────────
def get_next_report_number() -> int:
    scans = load_last_scan()
    n = scans.get("report_count", 0) + 1
    scans["report_count"] = n
    save_last_scan(scans)
    return n

# ── GEMMA4 ANALİZ ─────────────────────────────────────
def analyze_with_gemma(items: list[dict]) -> dict:
    """Top 10 öğeyi Gemma4'e gönder; yapılandırılmış analiz döndür.

    v1.1: Gemma4 kapalıysa otomatik başlatmayı dener. VRAM tahmini prompta eklendi.
    """
    if not items:
        return {"summary": "Bu taramada ilgili öğe bulunamadı.", "targets": [], "trend": "", "order": ""}

    # Gemma4 hazır değilse başlatmayı dene
    gemma_ok = check_and_launch_gemma4(wait_secs=60)
    if not gemma_ok:
        _log("Gemma4 çevrimdışı — fallback analiz kullanılıyor.")
        send_telegram("⚠️ <b>Hype Tarayıcı Uyarısı</b>\nGemma4 (analiz motoru) çevrimdışı — rapor ham veriden oluşturuldu.")
        return _fallback_analysis(sorted(items, key=lambda x: keyword_score(x), reverse=True)[:10])

    top_items = sorted(items, key=lambda x: keyword_score(x), reverse=True)[:10]

    # Fresh state read — her taramada güncel model bilgisini kullan
    try:
        _s = json.loads(_STATE_FILE.read_text(encoding="utf-8")) if _STATE_FILE.exists() else {}
        _cur_label = _s.get("label", LLAMA_MODEL)
        _cur_ctx   = int(_s.get("context_size", _LLAMA_CTX) or _LLAMA_CTX)
        _cur_size  = float(_s.get("size_gb", _LLAMA_SIZE_GB) or _LLAMA_SIZE_GB)
        _cur_toks  = float(_s.get("tok_s", _LLAMA_TOK_S) or _LLAMA_TOK_S) or 20.0
    except Exception:
        _cur_label, _cur_ctx, _cur_size, _cur_toks = LLAMA_MODEL, _LLAMA_CTX, _LLAMA_SIZE_GB, _LLAMA_TOK_S
    _ctx_k     = f"{_cur_ctx // 1024}K" if _cur_ctx % 1024 == 0 else str(_cur_ctx)
    _vram_note = f"MoE — experts CPU'da, GPU ~3-4GB" if _is_moe_model(_cur_label) else f"~{_cur_size:.1f}GB VRAM"

    items_text = ""
    for i, item in enumerate(top_items, 1):
        items_text += f"\n{i}. [{item['source'].upper()}] {item['name']}\n"
        items_text += f"   URL: {item['url']}\n"
        items_text += f"   Açıklama: {item.get('description', '')[:150]}\n"
        if item.get('stars_today'):
            items_text += f"   Bugünkü yıldız: {item['stars_today']}\n"
        stars = item.get('stars', 0) or item.get('likes', 0) or item.get('upvotes', 0)
        if stars:
            items_text += f"   Toplam yıldız/beğeni: {stars}\n"
        # VRAM tahmini önceden hesaplanmışsa göster
        vram_est = item.get("vram_est") or estimate_vram_from_name(item.get("name", ""))
        if vram_est and vram_est != "?":
            items_text += f"   Tahmini VRAM: {vram_est}\n"
        if item.get('tags'):
            items_text += f"   Etiketler: {', '.join(item['tags'][:6])}\n"

    prompt = f"""Sen Kuroshin İmparatorluğu'nun baş istihbarat subayısın.
Lordum için stratejik bir istihbarat brifing'i hazırlayacaksın.

HEDEF DONANIM:
- RTX 4060 Laptop, 8GB VRAM
- WSL2 Ubuntu, llama.cpp — GGUF format zorunlu
- Mevcut model: {_cur_label} ({_vram_note}, {_ctx_k} context, ~{_cur_toks:.0f} tok/s)
- Ajan Konseyi: Smolagents + ChromaDB RAG + BGE Reranker
- Hedef: Yerel, gizli, otonom çalışma

TARAMA SONUÇLARI:{items_text}

Şu 4 bölümü AYNEN bu etiketlerle yaz, başka metin ekleme:

BÖLÜM_1_ÖZET: tek güçlü cümle — bugünün en kritik bulgusu

BÖLÜM_2_TREND: 1-2 cümle — gözlemlenen teknolojik yön veya tehdit

BÖLÜM_3_HEDEFLER:
Her satır pipe ile ayır, başlık satırı yazma, sadece veri satırları:
ÖNCE|PROJE_ADI|PARAM|VRAM_GB|TOK_S|UYUM|NEDEN|HF_CLI_KOMUTU
Kurallar:
- ÖNCE: sadece rakam: 1=Hemen, 2=Test, 3=İzle
- PARAM: model parametre sayısı, örn "7B", "4B" — bilinmiyorsa "?"
- VRAM_GB: sayı ve birim, örn "4.3GB" — tarama verilerindeki "Tahmini VRAM" değerini kullan; yoksa parametre sayısına göre tahmin et. ASLA "?" yazma.
- TOK_S: {_cur_label} referans hız {_cur_toks:.0f} tok/s; küçük modeller için oranla tahmin et. Örn 1.5B → "60-80", 4B → "25-35". ASLA "?" yazma.
- UYUM: ✅ = VRAM≤7GB, ⚠️ = 7-8GB, ❌ = >8GB
- HF_CLI_KOMUTU: tam komut — "hf download KULLANICI/REPO_ADI --local-dir /root/kuroshin/models/KISA_AD --include '*.gguf'" — KISALTMA YAPMA, tam model ID yaz veya "—"

BÖLÜM_4_EMIR: 2-3 cümle tam, kesilmeden biten emir — Lordum'u harekete geçirir

Sadece bu 4 bölümü yaz. Türkçe."""

    try:
        resp = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1800,
            "temperature": 0.25,
        }, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"].strip()
        if not raw:
            finish = data["choices"][0].get("finish_reason", "?")
            _log(f"Gemma4 boş yanıt. finish_reason={finish}")
            return _fallback_analysis(top_items)
        return _parse_gemma_output(raw, top_items)
    except Exception as e:
        _log(f"Gemma4 analiz hatası: {e}")
        return _fallback_analysis(top_items)


def _parse_gemma_output(raw: str, items: list[dict]) -> dict:
    """Gemma4 çıktısını 4 bölüme ayır — markdown ve farklı format varyasyonlarına toleranslı."""
    import re
    result = {"summary": "", "trend": "", "targets": [], "order": "", "raw": raw}

    # Markdown bold/yıldızları temizle: **X** → X
    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', raw)

    # Çok satırlı bölümleri toplamak için state machine
    current_section = None
    section_lines = {"summary": [], "trend": [], "order": []}

    for line in clean.splitlines():
        stripped = line.strip()
        # Bölüm başlıkları — esnek eşleşme
        if re.search(r'BÖLÜM_?1|ÖZET', stripped, re.IGNORECASE):
            current_section = "summary"
            after = re.split(r'[:：]', stripped, 1)
            if len(after) > 1 and after[1].strip():
                section_lines["summary"].append(after[1].strip())
            continue
        elif re.search(r'BÖLÜM_?2|TREND', stripped, re.IGNORECASE):
            current_section = "trend"
            after = re.split(r'[:：]', stripped, 1)
            if len(after) > 1 and after[1].strip():
                section_lines["trend"].append(after[1].strip())
            continue
        elif re.search(r'BÖLÜM_?3|HEDEF', stripped, re.IGNORECASE):
            current_section = "targets"
            continue
        elif re.search(r'BÖLÜM_?4|EMİR|EMIR', stripped, re.IGNORECASE):
            current_section = "order"
            after = re.split(r'[:：]', stripped, 1)
            if len(after) > 1 and after[1].strip():
                section_lines["order"].append(after[1].strip())
            continue

        # Hedef satırı: pipe-separated, başlık satırını atla
        if "|" in stripped and current_section == "targets":
            parts = [p.strip() for p in stripped.split("|")]
            # Başlık satırını atla (sayısal öncelik olmayan ilk sütun)
            if not parts[0] or not re.search(r'\d', parts[0]):
                continue
            if len(parts) >= 4:
                pri_match = re.search(r'\d', parts[0])
                pri = pri_match.group() if pri_match else "3"
                raw_name = parts[1] if len(parts) > 1 else "?"
                raw_cli  = parts[7] if len(parts) > 7 else "—"

                # Gemma4 adı/cli'yı kesmiş olabilir — items'tan tam eşleşmeyi bul
                full_name = raw_name
                full_cli  = raw_cli
                name_lower = raw_name.lower().replace("-", "").replace("_", "")
                for src_item in items:
                    src_name = src_item.get("name", "")
                    src_lower = src_name.lower().replace("-", "").replace("_", "")
                    # İlk 12 karakter eşleşiyorsa tam adı kullan
                    if name_lower[:12] and name_lower[:12] in src_lower:
                        full_name = src_name
                        # CLI'yı URL'den yeniden inşa et
                        url = src_item.get("url", "")
                        hf_match = re.search(r'huggingface\.co/([^/?#\s]+/[^/?#\s]+)', url)
                        if hf_match:
                            model_id = hf_match.group(1)
                            full_cli = f"hf download {model_id} --local-dir /root/kuroshin/models/{model_id.split('/')[-1]} --include '*.gguf'"
                        break

                # Fallback: Gemma4 sahte isim verdiyse items listesinden al
                _generic = full_name.lower().strip() in ("test", "model", "?", "", "-", "gguf")
                if _generic and items:
                    _idx = len(result["targets"])
                    if _idx < len(items):
                        full_name = items[_idx].get("name", full_name)
                result["targets"].append({
                    "priority": pri,
                    "name": full_name[:60],
                    "params": parts[2] if len(parts) > 2 else "?",
                    "vram": parts[3] if len(parts) > 3 else "?",
                    "speed": parts[4] if len(parts) > 4 else "?",
                    "compat": parts[5] if len(parts) > 5 else "?",
                    "reason": parts[6][:150] if len(parts) > 6 else "",
                    "cli": full_cli,
                })
            continue

        # Normal metin satırı — mevcut bölüme ekle
        if current_section in section_lines and stripped:
            section_lines[current_section].append(stripped)

    result["summary"] = " ".join(section_lines["summary"])[:300]
    result["trend"]   = " ".join(section_lines["trend"])[:300]
    result["order"]   = " ".join(section_lines["order"])[:300]

    # Hiç parse edilmediyse ham metinden al
    if not result["summary"]:
        lines = [l.strip() for l in clean.splitlines() if l.strip() and "|" not in l]
        result["summary"] = lines[0][:200] if lines else "Analiz tamamlandı."

    return result


def _fallback_analysis(items: list[dict]) -> dict:
    """Gemma4 kapalıyken keyword tabanlı basit analiz."""
    targets = []
    for item in items[:8]:
        sc = keyword_score(item)
        if sc < 2:
            continue
        compat = "✅" if any(k in item.get("name","").lower() for k in ["4b","7b","8b","1b","3b","gguf","q4"]) else "⚠️"
        targets.append({
            "priority": "1" if sc >= 5 else ("2" if sc >= 3 else "3"),
            "name": item["name"][:40],
            "params": "?", "vram": "?", "speed": "?",
            "compat": compat,
            "reason": item.get("description", "")[:80],
        })
    return {
        "summary": "Gemma4 kapalıydı — keyword tabanlı otomatik analiz.",
        "trend": "Analiz servisi erişilemez durumdaydı.",
        "targets": targets,
        "order": "Servisleri kontrol et: /status",
    }


# ── RAPOR FORMATLA ────────────────────────────────────
def _tablo(targets: list[dict]) -> str:
    """ASCII tablo — Telegram monospace (pre) içinde hizalanır."""
    if not targets:
        return "Bu taramada kritik hedef tespit edilmedi."

    # Sütun genişlikleri sabit — Telegram dar ekrana göre
    C = {"pri": 6, "name": 30, "vram": 7, "spd": 7, "uyum": 4}
    sep = "─" * (C["pri"] + C["name"] + C["vram"] + C["spd"] + C["uyum"] + 9)

    badge_map = {"1": "🔴", "2": "🟡", "3": "🔵"}
    header = (
        f"{'PRI':<{C['pri']}} {'VARLIK':<{C['name']}} "
        f"{'VRAM':<{C['vram']}} {'tok/s':<{C['spd']}} {'UYUM':<{C['uyum']}}"
    )
    rows = [sep, header, sep]
    notes = []

    for t in targets:
        pri      = str(t.get("priority", "3"))
        badge    = badge_map.get(pri, "🔵")
        full_nm  = t.get("name", "?")
        name     = full_nm[:C["name"]]
        vram     = t.get("vram", "?")[:C["vram"]]
        spd      = t.get("speed", "?")[:C["spd"]]
        uyum     = t.get("compat", "?")

        rows.append(
            f"{badge:<{C['pri']}} {name:<{C['name']}} "
            f"{vram:<{C['vram']}} {spd:<{C['spd']}} {uyum}"
        )

        # Teknik dipnot satırı — tam model adı ve tam CLI komutu
        reason = t.get("reason", "")
        cli    = t.get("cli", "—")
        if reason or cli != "—":
            notes.append(f"  ↳ {full_nm}: {reason[:120]}")
            if cli and cli != "—":
                notes.append(f"    💾 {cli}")

    rows.append(sep)
    tablo = "\n".join(rows)
    dipnot = "\n".join(notes) if notes else ""
    return tablo + ("\n\n" + dipnot if dipnot else "")


def format_report(analysis: dict, scan_time: str, stats: dict, report_no: int,
                  all_filtered: list[dict] | None = None) -> str:
    session = "🌅 SABAH" if datetime.now().hour < 12 else "🌙 AKŞAM"

    summary = analysis.get("summary", "").strip()
    trend   = analysis.get("trend", "").strip()
    order   = analysis.get("order", "").strip()
    targets = analysis.get("targets", [])

    # Emir kesilmiş mi? Noktalama ile bitmiyorsa uyarı ekle (sessizce)
    if order and order[-1] not in ".!":
        order = order.rstrip("…,;") + "."

    # Ana tablo
    tablo_str = _tablo(targets)

    # "Diğer Kayda Değer Varlıklar" — top target dışındakiler keyword skoru ≥2
    diger_lines = []
    if all_filtered:
        top_names = {t.get("name", "").lower() for t in targets}
        diger = [
            i for i in all_filtered
            if i.get("name", "").lower()[:45] not in top_names and keyword_score(i) >= 2
        ][:5]
        for item in diger:
            sc = keyword_score(item)
            stars = item.get("stars", 0) or item.get("likes", 0) or item.get("upvotes", 0)
            star_str = f" ⭐{stars}" if stars else ""
            diger_lines.append(f"  • {item['name'][:45]}{star_str}")
            diger_lines.append(f"    {item['url']}")

    # Bölümleri birleştir
    parts = [
        f"🔭 <b>KUROSHIN İSTİHBARAT RAPORU #{report_no:04d}</b>",
        f"📅 {scan_time} — {session}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>YÖNETİCİ ÖZETİ</b>\n{summary or '—'}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if trend:
        parts += [f"🧭 <b>STRATEJİK TREND</b>\n{trend}", "━━━━━━━━━━━━━━━━━━━━━━━━"]

    parts += [
        "🎯 <b>ÖNCELİKLİ HEDEFLER</b>",
        f"<pre>{tablo_str}</pre>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if diger_lines:
        parts += [
            "📎 <b>DİĞER KAYDA DEĞER VARLIKLAR</b>",
            "\n".join(diger_lines),
            "━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

    if order:
        parts += [f"⚡ <b>HÜKÜMDAR EMRİ</b>\n<i>{order}</i>", "━━━━━━━━━━━━━━━━━━━━━━━━"]

    parts += [
        f"<i>📊 {stats.get('github',0)} GitHub · {stats.get('hf_papers',0)} HF Makale · {stats.get('hf_models',0)} GGUF → {stats.get('filtered',0)} elendi</i>",
        f"<i>⚔️ Kuroshin İstihbarat Servisi — #{report_no:04d}</i>",
    ]

    return "\n".join(parts)

# ── ANA TARAMA ────────────────────────────────────────
def run_scan(label: str = ""):
    scan_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    _log(f"=== TARAMA BAŞLIYOR: {scan_time} ===")
    send_telegram(
        f"🔭 <b>Hype Tarayıcı Başladı</b>\n"
        f"📅 {scan_time} {'— ' + label if label else ''}\n"
        f"Kaynaklar: GitHub Trending · HF Papers · HF GGUF\n"
        f"⏳ Sonuç ~2-3 dakika içinde gelecek."
    )

    # Tüm kaynakları tara
    github_items = scrape_github_trending("daily")
    hf_papers    = scrape_hf_papers()
    hf_models    = scrape_hf_new_models()

    all_items = github_items + hf_papers + hf_models
    _log(f"Toplam ham öğe: {len(all_items)}")

    # Keyword filtreleme
    scored = [(keyword_score(item), item) for item in all_items]
    scored.sort(key=lambda x: -x[0])
    filtered = [item for score, item in scored if score >= 1]
    _log(f"Filtre sonrası: {len(filtered)} öğe")

    stats = {
        "github": len(github_items),
        "hf_papers": len(hf_papers),
        "hf_models": len(hf_models),
        "filtered": len(filtered),
    }

    if not filtered:
        _log("Filtreye uyan öğe yok, rapor atlandı.")
        send_telegram(
            f"🔭 <b>Hype Tarayıcı Tamamlandı</b>\n"
            f"📅 {scan_time}\n"
            f"GitHub: {stats['github']} · HF Papers: {stats['hf_papers']} · HF Models: {stats['hf_models']}\n"
            f"⚠️ Eşik altında: hiçbir bulgu raporlanmadı."
        )
        return

    # Rapor numarası
    report_no = get_next_report_number()

    # Gemma4 analiz
    analysis = analyze_with_gemma(filtered)

    # Rapor oluştur
    report = format_report(analysis, scan_time, stats, report_no, all_filtered=filtered)

    # Dosyaya kaydet
    report_file = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    report_file.write_text(report, encoding="utf-8")
    _log(f"Rapor kaydedildi: {report_file}")

    # Telegram'a gönder
    send_telegram(report)
    _log("Rapor Telegram'a gönderildi.")

    # Son tarama zamanını kaydet
    scans = load_last_scan()
    scans["last"] = datetime.now().isoformat()
    scans["last_label"] = label or scan_time
    save_last_scan(scans)

    return report

# ── ZAMANLAYICI ───────────────────────────────────────
def should_scan_now() -> bool:
    """Şu an tarama zamanı mı? (planlı 09:00/21:00 ±1 saat)"""
    now = datetime.now()
    scans = load_last_scan()
    last_str = scans.get("last")

    if not last_str:
        return True  # İlk çalıştırma

    try:
        last_dt = datetime.fromisoformat(last_str)
    except Exception:
        return True

    elapsed_hours = (now - last_dt).total_seconds() / 3600
    if elapsed_hours < 11:
        return False

    hour = now.hour
    for scan_hour in SCAN_HOURS:
        if abs(hour - scan_hour) <= 1:
            return True

    return False


def should_catchup_now() -> bool:
    """PC geç açıldığında kaçırılan taramayı telafi et.

    Koşul: saat 09:00–20:59 arasındaysa VE son tarama >12 saat önceyse.
    Planlı saat pencerelerini (09 ±1, 21 ±1) kasıtlı dışarıda bırakır —
    oradaki taramayı should_scan_now() zaten yakalar.
    """
    now = datetime.now()
    hour = now.hour
    if not (9 <= hour <= 20):
        return False  # Gece veya akşam tarama saatinde değil

    scans = load_last_scan()
    last_str = scans.get("last")
    if not last_str:
        return True  # Hiç taranmamış

    try:
        last_dt = datetime.fromisoformat(last_str)
        elapsed_hours = (now - last_dt).total_seconds() / 3600
        if elapsed_hours > 12:
            _log(f"Catch-up tetiklendi: son tarama {elapsed_hours:.1f} saat önce")
            return True
    except Exception:
        return True

    return False


# ── CATCHUP BİLDİRİMİ ────────────────────────────────
def check_catchup():
    """Kaçırılan tarama varsa Telegram'a bildir (taramayı başlatmaz)."""
    scans = load_last_scan()
    last_str = scans.get("last")
    if not last_str:
        _log("İlk çalıştırma — catchup yok.")
        return

    try:
        last_dt = datetime.fromisoformat(last_str)
        elapsed_hours = (datetime.now() - last_dt).total_seconds() / 3600
        if elapsed_hours < 1:
            return
        missed = min(int(elapsed_hours / 12), MAX_CATCHUP_DAYS * 2)
        if missed > 0:
            _log(f"Kaçırılan tarama: ~{missed} ({elapsed_hours:.1f} saat)")
            send_telegram(
                f"⚠️ <b>Hype Tarayıcı Uyandı</b>\n"
                f"Son tarama: {last_str[:16]}\n"
                f"~{elapsed_hours:.0f} saat kapalıydım.\n"
                f"Catch-up taraması başlıyor..."
            )
    except Exception as _e:
        _log(f"[HYPE] HATA: {_e}")

# ── ANA DÖNGÜ ─────────────────────────────────────────
PID_FILE = "/tmp/kuroshin_hype.pid"

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

    _log(f"🔭 Kuroshin Hype Tarayıcı BAŞLADI ({'daemon' if daemon_mode else 'cron'})")
    _log(f"Tarama saatleri: {SCAN_HOURS}")

    if daemon_mode:
        _sf = Path("/tmp/kuroshin_hype.started")
        if not _sf.exists():
            _sf.touch()
            _next = next((h for h in SCAN_HOURS if h > datetime.now().hour), SCAN_HOURS[0])
            send_telegram(
                f"🔭 <b>Hype Tarayıcı Daemon Başladı</b>\n"
                f"Tarama saatleri: {SCAN_HOURS}\n"
                f"⏰ Sonraki tarama: saat {_next:02d}:00"
            )

    if daemon_mode:
        # Boot'ta tarama YOK — sadece 09:00 ve 21:00'de çalışır
        _log("Hype Scanner daemon başladı — 09:00 ve 21:00 bekleniyor.")
        while True:
            try:
                time.sleep(1800)
                if should_scan_now():
                    now = datetime.now()
                    label = f"{now.strftime('%d.%m.%Y')} {'sabah' if now.hour < 12 else 'akşam'}"
                    _log(f"Planlı tarama: {label}")
                    run_scan(label=label)
                else:
                    _next = next((h for h in SCAN_HOURS if h > datetime.now().hour), SCAN_HOURS[0])
                    _log(f"Tarama zamanı değil. Sonraki: {_next:02d}:00")
            except KeyboardInterrupt:
                _log("Hype Tarayıcı durduruldu.")
                break
            except Exception:
                _log(f"Döngü hatası: {traceback.format_exc()}")
                time.sleep(60)
    else:
        # Cron modu: tek seferlik çalış ve çık
        _log("Cron modu — tek seferlik tarama")
        try:
            run_scan(label="cron")
        except Exception:
            _log(f"Tarama hatası: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
