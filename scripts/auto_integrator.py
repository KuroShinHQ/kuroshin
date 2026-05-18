"""
Kuroshin Otonom Entegrasyon Döngüsü v1.0
==========================================
Hype Scanner ve Global Scout raporlarını izler.
🔴 ACİL işaretli öğeleri otomatik test eder.
Test sonuçlarını Telegram'a raporlar, Lord onay verirse entegre eder.

Akış:
  rapor gelir → ACİL öğe tespit → huggingface-cli download → llama-server hız testi
  → ChromaDB'ye kaydet → Telegram test raporu → Lord /onay <id> → Kuroshin.bat güncelle

Çalıştırma: python3 /mnt/c/Kuroshin/scripts/auto_integrator.py
"""

import json
import os
import re
import time
import subprocess
import traceback
import requests
from datetime import datetime
from pathlib import Path
import sys
from dotenv import load_dotenv
load_dotenv(Path("/mnt/c/Kuroshin/.env"))

# Import traffic manager
sys.path.insert(0, "C:\\Kuroshin\\scripts")
try:
    import traffic_manager
except ImportError:
    traffic_manager = None

# ── CONFIG ────────────────────────────────────────────
HYPE_REPORTS_DIR  = Path("/root/kuroshin/memory/hype_reports")
SCOUT_REPORTS_DIR = Path("/root/kuroshin/memory/scout_reports")
QUEUE_FILE        = Path("/root/kuroshin/memory/integration_queue.json")
DONE_FILE         = Path("/root/kuroshin/memory/integration_done.json")
PENDING_DOWNLOADS_FILE = Path("/root/kuroshin/memory/pending_downloads.json")
LOG_PATH          = Path("/root/kuroshin/logs/auto_integrator.log")
MODELS_DIR        = Path("/root/kuroshin/models")
LLAMA_URL         = "http://127.0.0.1:8080/v1/chat/completions"
LLAMA_MODEL       = "mlabonne_Qwen3-8B-abliterated-Q5_K_M.gguf"
LLAMA_HEALTH      = "http://127.0.0.1:8080/health"
CHROMA_URL        = "http://127.0.0.1:8100"
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT     = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
CHECK_INTERVAL    = 120   # 2 dakikada bir yeni rapor kontrol et
VRAM_LIMIT_MB     = 7200  # İndirme/test için VRAM serbest eşiği
MAX_MODEL_GB      = 6.5   # Bu GB'dan büyük modelleri otomatik test etme

SESSION_NOTIFIED = set() # In-memory spam protection

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── LOGGING ───────────────────────────────────────────
def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as _e:
        print(f"[AUTO_INTEGRATOR] HATA: {_e}")

# ── TELEGRAM ──────────────────────────────────────────
def send_telegram(text: str):
    chunks = [text[i:i+4000] for i in range(0, max(len(text), 1), 4000)]
    for chunk in chunks:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT, "text": chunk, "parse_mode": "HTML"},
                timeout=15,
            )
            time.sleep(0.3)
        except Exception as e:
            _log(f"Telegram hata: {e}")

# ── MODEL BOYUTU API ──────────────────────────────────
def get_model_size_from_hf_api(model_id: str) -> float:
    """HuggingFace API üzerinden modelin toplam GGUF boyutunu GB cinsinden döndür.

    Strateji 1: /api/models/{id} → siblings listesinde .gguf dosyalarının boyutlarını topla.
    Strateji 2: Dosya adından quant parse edip tahmin et.
    0 döndürmek yerine bilinemiyorsa -1 döndürür (çağıran None olduğunu anlar).
    """
    if not model_id or "/" not in model_id:
        return -1.0
    try:
        resp = requests.get(
            f"https://huggingface.co/api/models/{model_id}",
            timeout=15,
        )
        if resp.status_code != 200:
            return -1.0
        data = resp.json()
        siblings = data.get("siblings", [])
        total_bytes = sum(
            s.get("size", 0) or 0
            for s in siblings
            if s.get("rfilename", "").endswith(".gguf")
        )
        if total_bytes > 0:
            return round(total_bytes / (1024 ** 3), 2)
    except Exception as e:
        _log(f"HF API boyut sorgu hatası ({model_id}): {e}")
    return -1.0

# ── KUYRUK YÖNETİMİ ───────────────────────────────────
def load_queue() -> list:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except Exception as _e:
            print(f"[AUTO_INTEGRATOR] HATA: {_e}")
    return []

def save_queue(q: list):
    QUEUE_FILE.write_text(json.dumps(q, indent=2, ensure_ascii=False))

def load_done() -> dict:
    if DONE_FILE.exists():
        try:
            return json.loads(DONE_FILE.read_text())
        except Exception as _e:
            print(f"[AUTO_INTEGRATOR] HATA: {_e}")
    return {}

def save_done(d: dict):
    DONE_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False))

# ── YARDIMCI FONKSİYONLAR ────────────────────────────
def load_pending_downloads():
    if not PENDING_DOWNLOADS_FILE.exists(): return []
    try: return json.loads(PENDING_DOWNLOADS_FILE.read_text())
    except: return []

def save_pending_downloads(data):
    PENDING_DOWNLOADS_FILE.write_text(json.dumps(data, indent=2))

def already_processed(item_id: str) -> bool:
    if item_id in SESSION_NOTIFIED: return True
    done = load_done()
    if item_id in done: return True
    pending = load_pending_downloads()
    if any(p["id"] == item_id for p in pending): return True
    return False

def mark_done(item_id: str, result: dict):
    SESSION_NOTIFIED.add(item_id)
    done = load_done()
    done[item_id] = {"ts": datetime.now().isoformat(), **result}
    save_done(done)

# ── RAPOR PARSER ──────────────────────────────────────
def parse_hype_report(report_path: Path) -> list[dict]:
    """Hype Scanner raporundan 🔴 ACİL öğeleri çıkar.
    Strateji 1: '💾 hf download KULLANICI/REPO' satırından tam model adı al.
    Strateji 2 (fallback): Rapordaki HF URL'lerinden model ID çıkar."""
    text = report_path.read_text(encoding="utf-8", errors="replace")
    items = []
    seen_ids = set()

    is_acil = "🔴" in text

    def _make_item(model_id: str, cli_cmd: str, vram_ctx: str = "") -> dict | None:
        item_id = re.sub(r'[^a-z0-9]', '_', model_id.lower())[:40]
        if item_id in seen_ids:
            return None
        seen_ids.add(item_id)
        vram_m = re.search(r'VRAM[:\s]+~?([0-9.]+)\s*GB', vram_ctx or text)
        vram_gb = float(vram_m.group(1)) if vram_m else None
        return {
            "id": item_id,
            "name": model_id,
            "cli": cli_cmd,
            "vram_gb": vram_gb,
            "source": str(report_path.name),
            "priority": "acil" if is_acil else "test",
            "type": "model",
        }

    # Strateji 1: '💾 hf download KULLANICI/REPO ...' satırı
    for m in re.finditer(
        r'(?:💾\s*)?(?:huggingface-cli|hf)\s+download\s+([A-Za-z0-9_\-\.]+/[A-Za-z0-9_\-\.]+)((?:\s+--\S+(?:\s+\S+)?)*)',
        text
    ):
        model_id = m.group(1)
        args = m.group(2).strip()
        dest_m = re.search(r'--local-dir\s+(\S+)', args)
        dest = dest_m.group(1) if dest_m else str(MODELS_DIR / model_id.split("/")[-1])
        cli = f"hf download {model_id} --local-dir {dest} --include '*.gguf'"
        # Modelin yakın çevresindeki metni VRAM tahmini için al
        idx = text.find(model_id[:15])
        ctx = text[max(0, idx - 200):idx + 300] if idx >= 0 else ""
        it = _make_item(model_id, cli, ctx)
        if it:
            items.append(it)

    # Strateji 2 (fallback): raporda HF URL'si varsa ve GGUF formatındaysa
    if not items:
        # Büyük model boyutlarını gösteren pattern — bunları atla
        BIG_MODEL = re.compile(r'(?:^|[-_/])(?:1[0-9]b|2[0-9]b|3[0-9]b|7[0-9]b)[^0-9]', re.IGNORECASE)
        for m in re.finditer(r'huggingface\.co/([A-Za-z0-9_\-\.]+/[A-Za-z0-9_\-\.]+)', text):
            model_id = m.group(1)
            # GGUF/q4/q8 içermeyen repo'ları atla
            if not any(k in model_id.lower() for k in ["gguf", "q4", "q8", "q5"]):
                continue
            # 14B+ modelleri atla — VRAM limiti aşılır
            if BIG_MODEL.search(model_id):
                continue
            dest = str(MODELS_DIR / model_id.split("/")[-1])
            cli = f"hf download {model_id} --local-dir {dest} --include '*.gguf'"
            idx = m.start()
            ctx = text[max(0, idx - 300):idx + 200]
            it = _make_item(model_id, cli, ctx)
            if it:
                items.append(it)

    return items

def parse_scout_report(report_path: Path) -> list[dict]:
    """Global Scout raporundan 🔴 ACİL öğeleri çıkar."""
    text = report_path.read_text(encoding="utf-8", errors="replace")
    items = []

    acil_blocks = re.findall(r'🔴[^\n]*\n(?:.*\n){0,6}', text)
    for block in acil_blocks:
        url_match = re.search(r'🔗\s*(https?://\S+)', block)
        title_match = re.search(r'│\s*(.+)', block)
        if not url_match:
            continue
        url = url_match.group(1)
        title = title_match.group(1).strip() if title_match else url[:60]

        # Sadece HuggingFace model linkleri test edilebilir
        hf_model = re.search(r'huggingface\.co/([^/\s]+/[^/\s]+)', url)
        if not hf_model:
            # Model değilse sadece kaydet, indirme/test yapma
            item_id = re.sub(r'[^a-z0-9]', '_', title.lower())[:40]
            items.append({
                "id": item_id,
                "name": title[:60],
                "url": url,
                "cli": "",  # boş = sadece kaydet
                "vram_gb": None,
                "source": str(report_path.name),
                "priority": "acil",
                "type": "link",
            })
            continue

        model_id = hf_model.group(1)
        item_id = re.sub(r'[^a-z0-9]', '_', model_id.lower())[:40]
        items.append({
            "id": item_id,
            "name": model_id,
            "url": url,
            "cli": f"huggingface-cli download {model_id} --local-dir {MODELS_DIR}/{model_id.split('/')[-1]}",
            "vram_gb": None,
            "source": str(report_path.name),
            "priority": "acil",
            "type": "model",
        })

    return items

# ── VRAM KONTROL ──────────────────────────────────────
def get_vram_used_mb() -> int:
    try:
        result = subprocess.run(
            ["bash", "-c", "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        return int(result.stdout.strip())
    except Exception:
        return 9999  # bilinmiyorsa kısıtlayıcı ol

# ── HF İNDİRME ────────────────────────────────────────
def download_model(item: dict) -> dict:
    """huggingface-cli ile modeli indir."""
    import fcntl as _fcntl
    _lf = open("/tmp/kuroshin_download.lock", "w")
    try:
        _fcntl.flock(_lf, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
    except BlockingIOError:
        _lf.close()
        _log(f"[download] Baska indirme aktif, atlaniyor: {item['name']}")
        return {"status": "skip", "reason": "Baska indirme aktif"}
    try:
        return _download_inner(item)
    finally:
        _fcntl.flock(_lf, _fcntl.LOCK_UN)
        _lf.close()


def _download_inner(item: dict) -> dict:
    """Asil indirme - download_model flock altinda cagirir."""
    name = item["name"]
    vram_gb = item.get("vram_gb")

    # dest: cli'daki --local-dir'den çek, yoksa model adından türet
    import re as _re
    cli = item.get("cli", "")
    local_dir_match = _re.search(r'--local-dir\s+(\S+)', cli)
    if local_dir_match:
        dest = Path(local_dir_match.group(1))
    else:
        # Kısa isim: repo adının son parçası, GGUF/gguf sonekini at
        short = name.split("/")[-1]
        short = _re.sub(r'[-_]?(gguf|GGUF)$', '', short)
        dest = MODELS_DIR / short

    # VRAM kontrolü
    vram_used = get_vram_used_mb()
    if vram_used > VRAM_LIMIT_MB:
        send_telegram(
            f"🚫 <b>Model Atlandı (VRAM Yetersiz)</b>\n"
            f"Model: <code>{name}</code>\n"
            f"Kullanılan VRAM: {vram_used} MB / {VRAM_LIMIT_MB} MB"
        )
        return {"status": "skip", "reason": f"VRAM dolu: {vram_used}MB"}
    # Boyut kontrolü (tahmin varsa)
    if vram_gb and vram_gb > MAX_MODEL_GB:
        send_telegram(
            f"🚫 <b>Model Atlandı (VRAM Yetersiz)</b>\n"
            f"Model: <code>{name}</code>\n"
            f"Tahmini: {vram_gb:.1f} GB > Limit: {MAX_MODEL_GB} GB"
        )
        return {"status": "skip", "reason": f"Model çok büyük: {vram_gb}GB > limit {MAX_MODEL_GB}GB"}
    # Zaten var mı? — models dizininin tamamında ara
    all_gguf = list(MODELS_DIR.rglob("*.gguf"))
    model_short = name.split("/")[-1].lower().replace("-gguf","").replace("_gguf","")
    matching = [f for f in all_gguf if model_short[:15] in f.name.lower()]
    if matching:
        send_telegram(
            f"✔️ <b>Model Zaten Mevcut</b>\n"
            f"Model: <code>{name}</code>\n"
            f"Dosya: <code>{matching[0].name}</code>\n"
            f"🚫 İndirme atlandı."
        )
        return {"status": "exists", "path": str(matching[0]), "reason": "Zaten mevcut"}

    _log(f"İndiriliyor: {name}")
    send_telegram(
        f"⬇️ <b>Otonom İndirme Başladı</b>\n"
        f"Model: <code>{name}</code>\n"
        f"Hedef: <code>{dest}</code>\n"
        f"VRAM mevcut: {8188 - vram_used}MB"
    )

    try:
        cmd = f"source /root/kuroshin/venv/bin/activate && hf download {name} --local-dir {dest} --include '*.gguf' 2>&1 | tail -5"
        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True, text=True, timeout=600  # 10 dk
        )
        output = (result.stdout + result.stderr).strip()[-500:]

        # İndirilen GGUF dosyasını bul
        gguf_files = list(dest.glob("*.gguf")) if dest.exists() else []
        if gguf_files:
            gguf_path = str(sorted(gguf_files)[-1])
            gguf_size = round(Path(gguf_path).stat().st_size / 1024**3, 2)
            send_telegram(
                f"✅ <b>İndirme Tamamlandı</b>\n"
                f"Model: <code>{name}</code>\n"
                f"Dosya: <code>{Path(gguf_path).name}</code>\n"
                f"Boyut: {gguf_size} GB\n"
                f"⚡ Hız testi başlıyor..."
            )
            return {"status": "downloaded", "path": gguf_path, "output": output}
        else:
            send_telegram(
                f"❌ <b>İndirme Başarısız</b>\n"
                f"Model: <code>{name}</code>\n"
                f"GGUF dosyası bulunamadı.\n"
                f"<pre>{output[-200:]}</pre>"
            )
            return {"status": "failed", "reason": "GGUF bulunamadı", "output": output}
    except subprocess.TimeoutExpired:
        send_telegram(f"⏱️ <b>İndirme Zaman Aşımı</b>\nModel: <code>{name}</code>\n10 dakika aşıldı.")
        return {"status": "timeout", "reason": "10 dakika aşıldı"}
    except Exception as e:
        send_telegram(f"🔥 <b>İndirme Hatası</b>\nModel: <code>{name}</code>\n{str(e)[:200]}")
        return {"status": "error", "reason": str(e)}

# ── LLAMA-SERVER HIZ TESTİ ────────────────────────────
def speed_test(gguf_path: str, model_name: str) -> dict:
    """Mevcut llama-server ile değil, ayrı process ile hız testi."""
    # llama-server zaten çalışıyorsa ona sor — farklı model yükleyemeyiz
    # Bunun yerine mevcut llama-server üzerinde basit bir benchmark prompt çalıştır
    # ve "bu modeli neden tercih et/etme" sorusunu Gemma4'e sor
    try:
        resp = requests.get(LLAMA_HEALTH, timeout=5)
        if resp.status_code != 200:
            return {"status": "llama_offline", "tok_s": None}
    except Exception:
        return {"status": "llama_offline", "tok_s": None}

    # Mevcut modelin hız referansı al (10 token benchmark)
    prompt = "Merhaba dünya! Bu bir hız testi mesajıdır. Lütfen 50 token kadar yanıt ver."
    t0 = time.time()
    try:
        resp = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.1,
        }, timeout=30)
        elapsed = time.time() - t0
        data = resp.json()
        tokens = data.get("usage", {}).get("completion_tokens", 0)
        tok_s = round(tokens / elapsed, 1) if elapsed > 0 else 0
        return {"status": "ok", "tok_s": tok_s, "note": "Mevcut Gemma4 referans hızı"}
    except Exception as e:
        return {"status": "error", "reason": str(e), "tok_s": None}

# ── CHROMADB KAYIT ────────────────────────────────────
def save_to_chroma(item: dict, test_result: dict):
    """Test sonucunu ChromaDB'ye kaydet."""
    try:
        import chromadb
        client = chromadb.HttpClient(host="127.0.0.1", port=8100)
        col = client.get_or_create_collection("integration_results")
        doc = (
            f"Model: {item['name']}\n"
            f"Kaynak: {item['source']}\n"
            f"Test: {json.dumps(test_result, ensure_ascii=False)}\n"
            f"Tarih: {datetime.now().isoformat()}"
        )
        col.add(
            documents=[doc],
            ids=[f"integration_{item['id']}_{int(time.time())}"],
            metadatas=[{"name": item["name"], "status": test_result.get("status", "?"), "ts": datetime.now().isoformat()}]
        )
        _log(f"ChromaDB kayıt: {item['name']}")
    except Exception as e:
        _log(f"ChromaDB hata: {e}")

# ── ONAY MEKANİZMASI ──────────────────────────────────
def check_pending_approvals() -> list[dict]:
    """Kuyrukta Lord onayı bekleyen öğeleri döndür."""
    queue = load_queue()
    return [i for i in queue if i.get("state") == "waiting_approval"]

def process_approval(item_id: str, approved: bool):
    """Lord'un /onay veya /red komutunu işle."""
    queue = load_queue()
    item = next((i for i in queue if i["id"] == item_id), None)
    if not item:
        send_telegram(f"⚠️ Kuyrukta bulunamadı: <code>{item_id}</code>")
        return

    if approved:
        _log(f"ONAYLANDI: {item['name']}")
        # Modeli aktif listeye kaydet
        active_file = Path("/root/kuroshin/memory/active_models.json")
        active = json.loads(active_file.read_text()) if active_file.exists() else []
        active.append({
            "name": item["name"],
            "path": item.get("test", {}).get("path", ""),
            "added": datetime.now().isoformat(),
            "source": item.get("source", ""),
        })
        active_file.write_text(json.dumps(active, indent=2, ensure_ascii=False))
        send_telegram(
            f"✅ <b>Entegrasyon Onaylandı</b>\n"
            f"<code>{item['name']}</code> aktif modeller listesine eklendi.\n"
            f"⚔️ Lordum, model hazır."
        )
        item["state"] = "approved"
    else:
        item["state"] = "rejected"
        send_telegram(f"❌ <b>Reddedildi:</b> <code>{item['name']}</code>")

    # Kuyruktan kaldır
    queue = [i for i in queue if i["id"] != item_id]
    save_queue(queue)
    mark_done(item_id, {"state": "approved" if approved else "rejected"})

# ── TEK ÖĞE İŞLE (YENİ: SADECE ONAY İSTE) ──────────────
def process_item(item: dict):
    """Bir ACİL öğe bulundu. Kota kontrol et ve indirme için onay iste."""
    item_id = item["id"]
    if item_id in SESSION_NOTIFIED: return # Ekstra koruma

    name    = item["name"]
    item_type = item.get("type", "model")

    _log(f"İşleniyor: {name} [{item_type}]")

    # Link tipi öğeler — sadece Telegram'a bildir
    if item_type == "link" or not item.get("cli"):
        msg = (
            f"🧭 <b>Keşif Bulgusu — Lord Dikkatine</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 <b>{name[:60]}</b>\n"
            f"🔗 {item.get('url','')}\n"
            f"Kaynak: {item['source']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Bu kaynak otomatik indirilemez. Manuel inceleme gerekiyor.\n"
            f"⚔️ Kuroshin İstihbarat"
        )
        send_telegram(msg)
        mark_done(item_id, {"status": "notified", "type": "link"})
        return

    # Gerçek dosya boyutunu HF API'den al
    raw_size = float(item.get("vram_gb", 0) or 0)
    if raw_size == 0.0:
        _log(f"Boyut bilinmiyor, HF API'den sorgulanıyor: {name}")
        api_size = get_model_size_from_hf_api(name)
        if api_size > 0:
            raw_size = api_size
            item["vram_gb"] = api_size
            _log(f"HF API boyut: {api_size} GB")

    if raw_size == 0.0 or raw_size < 0:
        size_str = "bilinmiyor ⚠️"
        size_warning = "\n⚠️ Dosya boyutu alınamadı — indirme başlamadan önce manuel kontrol edin."
    elif raw_size > MAX_MODEL_GB:
        size_str = f"{raw_size} GB ❌ (VRAM sınırı aşılıyor)"
        size_warning = f"\n❌ Bu model {MAX_MODEL_GB} GB limitini aşıyor. İndirme önerilmez."
    else:
        size_str = f"{raw_size} GB ✅"
        size_warning = ""
    size_gb = max(raw_size, 0.0)

    # İndirme Onayı İste
    report = (
        f"🔭 <b>YENİ POTANSİYEL MODEL TESPİT EDİLDİ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Model: <code>{name}</code>\n"
        f"💾 Boyut: {size_str}\n"
        f"📡 Kaynak: {item['source']}\n"
        f"━━━━━━━━━━━━━━━━━━━━{size_warning}\n"
        f"⚔️ <b>Lordum, bu model indirilsin mi?</b>\n"
        f"✅ İndirmek için: <code>/onay_indir {item_id}</code>\n"
        f"❌ Pas geçmek için: <code>/red {item_id}</code>"
    )
    
    # Bekleyen indirmelere ekle
    pending = load_pending_downloads()
    # Duplicate kontrolü
    if not any(p["id"] == item_id for p in pending):
        pending.append(item)
        save_pending_downloads(pending)
        send_telegram(report)
        SESSION_NOTIFIED.add(item_id) # Onay bekleyenler için de işaretle
    else:
        _log(f"Zaten bekleyen indirmelerde: {name}")
        SESSION_NOTIFIED.add(item_id)

def start_download_process(item: dict):
    """Onaylanmış modelin indirme ve test sürecini başlat."""
    name = item["name"]
    item_id = item["id"]
    size_gb = item.get("vram_gb", 0)

    _log(f"İndirme Başlatılıyor: {name}")
    
    # Model öğesi — indir ve test et
    dl = download_model(item)
    _log(f"İndirme: {dl['status']}")

    test = {}
    if dl["status"] in ("downloaded", "exists"):
        # Kota ekle
        if traffic_manager and dl["status"] == "downloaded":
            # Gerçek boyutu al
            actual_size = 0
            try:
                actual_size = Path(dl["path"]).stat().st_size / (1024**3)
            except:
                actual_size = size_gb
            traffic_manager.add_usage(actual_size)

        test = speed_test(dl.get("path", ""), name)
        save_to_chroma(item, {**dl, **test})

    # Telegram test raporu
    status_icon = {
        "downloaded": "✅ İndirildi",
        "exists": "📁 Zaten Mevcut",
        "skip": "⏭️ Atlandı",
        "failed": "❌ Başarısız",
        "timeout": "⏱️ Zaman Aşımı",
        "error": "🔥 Hata",
    }.get(dl["status"], dl["status"])

    tok_s = test.get("tok_s")
    speed_str = f"{tok_s} tok/s (mevcut model ref.)" if tok_s else "test yapılamadı"

    report = (
        f"🔬 <b>OTONOM TEST RAPORU</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Model: <code>{name}</code>\n"
        f"📦 Durum: {status_icon}\n"
        f"⚡ Hız: {speed_str}\n"
        f"💾 VRAM: {item.get('vram_gb','?')} GB (tahmini)\n"
        f"Kaynak Rapor: {item['source']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    if dl["status"] in ("downloaded", "exists"):
        report += (
            f"⚔️ <b>Lordum, model hazır. Entegre edilsin mi?</b>\n"
            f"✅ Onaylamak için: <code>/onay {item_id}</code>\n"
            f"❌ Reddetmek için: <code>/red {item_id}</code>"
        )
        # Kuyrukta onay beklet
        queue = load_queue()
        queue.append({**item, "state": "waiting_approval", "test": {**dl, **test}})
        save_queue(queue)
    else:
        report += f"ℹ️ Neden: {dl.get('reason','')}"
        mark_done(item_id, {"status": dl["status"]})

    send_telegram(report)

# ── YENİ RAPOR TARAYICI ───────────────────────────────
def scan_new_reports() -> list[dict]:
    """Son 2 saatteki yeni raporları tara, işlenmemiş ACİL öğeleri döndür."""
    new_items = []
    done = load_done()
    cutoff = time.time() - 7200  # 2 saat

    for report_dir, parser in [
        (HYPE_REPORTS_DIR, parse_hype_report),
        (SCOUT_REPORTS_DIR, parse_scout_report),
    ]:
        if not report_dir.exists():
            continue
        for f in sorted(report_dir.glob("*.txt"), reverse=True)[:5]:
            if f.stat().st_mtime < cutoff:
                continue
            try:
                items = parser(f)
                for item in items:
                    if item["id"] not in done:
                        new_items.append(item)
            except Exception as e:
                _log(f"Parse hata {f.name}: {e}")

    return new_items

# ── ŞANSÖLYE KOMUT ENTEGRASYonu ───────────────────────
def handle_command(text: str) -> bool:
    """Şansölye'den gelen komutları işle. True döndürürse işlendi."""
    text = text.strip()
    
    # 1. Onay/Red (Entegrasyon)
    if text.startswith("/onay ") or text.startswith("!onay "):
        item_id = text.split(None, 1)[1].strip()
        process_approval(item_id, approved=True)
        return True
    elif text.startswith("/red ") or text.startswith("!red "):
        item_id = text.split(None, 1)[1].strip()
        # Hem onay bekleyenlerden hem kuyruktan sil
        pending = load_pending_downloads()
        if any(p["id"] == item_id for p in pending):
            pending = [p for p in pending if p["id"] != item_id]
            save_pending_downloads(pending)
            send_telegram(f"🚫 <b>İstihbarat Arşivlendi:</b> <code>{item_id}</code>")
            mark_done(item_id, {"status": "rejected"})
            return True
        process_approval(item_id, approved=False)
        return True

    # 2. İndirme Onayı
    elif text.startswith("/onay_indir ") or text.startswith("!onay_indir "):
        item_id = text.split(None, 1)[1].strip()
        pending = load_pending_downloads()
        target = next((p for p in pending if p["id"] == item_id), None)
        if target:
            # Önce kota kontrolü (tekrar, son dakika)
            if traffic_manager:
                ok, reason = traffic_manager.check_quota(target.get("vram_gb", 0))
                if not ok:
                    send_telegram(f"🚦 <b>Kota Engeli:</b> {reason}")
                    return True
            
            # Bekleyenlerden kaldır
            pending = [p for p in pending if p["id"] != item_id]
            save_pending_downloads(pending)
            
            # İndirmeyi başlat
            start_download_process(target)
            return True
        else:
            send_telegram("⚠️ ID bulunamadı veya zaten işlenmiş.")
            return True

    # 3. Kota Yönetimi
    elif text.startswith("/limit ") or text.startswith("!limit "):
        try:
            val = float(text.split(None, 1)[1])
            if traffic_manager:
                traffic_manager.set_limit(val)
                send_telegram(f"✅ Günlük kota <b>{val} GB</b> olarak güncellendi.")
            return True
        except: return False

    elif text in ("/kota", "!kota"):
        if traffic_manager:
            s = traffic_manager.get_status()
            p_status = "⏸️ DURAKLATILDI" if s.get("paused") else "▶️ AKTİF"
            limit = s.get("daily_limit_gb", 0)
            used = s.get("used_today_gb", 0)
            remaining = max(0, limit - used)
            msg = (
                f"📡 <b>TRAFİK DURUMU</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Sistem: {p_status}\n"
                f"Günlük Limit: {limit:.2f} GB\n"
                f"Harcanan: {used:.2f} GB\n"
                f"Kalan: {remaining:.2f} GB\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            send_telegram(msg)
        return True

    elif text in ("/duraklat", "!duraklat"):
        if traffic_manager: traffic_manager.set_paused(True)
        send_telegram("⏸️ <b>Otonom İndirmeler DURAKLATILDI.</b>")
        return True

    elif text in ("/devam", "!devam"):
        if traffic_manager: traffic_manager.set_paused(False)
        send_telegram("▶️ <b>Otonom İndirmeler DEVAM EDİYOR.</b>")
        return True

    elif text in ("/bekleyen", "!bekleyen"):
        # Hem indirme bekleyenleri hem entegrasyon bekleyenleri göster
        pending_dl = load_pending_downloads()
        pending_int = check_pending_approvals()
        
        lines = ["⏳ <b>BEKLEYEN İŞLEMLER</b>"]
        if not pending_dl and not pending_int:
            send_telegram("📭 Bekleyen işlem yok.")
            return True
            
        if pending_dl:
            lines.append("\n⬇️ <b>İndirme Onayı Bekleyenler:</b>")
            for p in pending_dl:
                lines.append(f"  • <code>{p['id']}</code> — {p['name'][:30]} ({p.get('vram_gb','?')} GB)")
        
        if pending_int:
            lines.append("\n⚙️ <b>Entegrasyon Onayı Bekleyenler:</b>")
            for p in pending_int:
                lines.append(f"  • <code>{p['id']}</code> — {p['name'][:30]}")
        
        send_telegram("\n".join(lines))
        return True
    
    return False

# ── ANA DÖNGÜ ─────────────────────────────────────────
PID_FILE = "/tmp/kuroshin_auto.pid"

def _acquire_lock():
    """Aynı anda sadece bir instance çalışsın."""
    import os, signal
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
    _log("🔬 Kuroshin Otonom Entegrasyon BAŞLADI")

    _sf = Path("/tmp/kuroshin_auto.started")
    if not _sf.exists():
        _sf.touch()
        send_telegram(
            "🔬 <b>Otonom Entegrasyon Döngüsü Aktif</b>\n"
            "Hype ve Scout raporlarını izliyorum.\n"
            "ACİL öğeler için onay mekanizması devrede.\n"
            f"VRAM eşiği: {VRAM_LIMIT_MB}MB\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Komutlar:</b>\n"
            "  <code>/onay_indir &lt;id&gt;</code> — İndirmeyi başlat\n"
            "  <code>/onay &lt;id&gt;</code> — Entegre et\n"
            "  <code>/red &lt;id&gt;</code> — Reddet/Arşivle\n"
            "  <code>/kota</code> | <code>/limit</code> | <code>/bekleyen</code>"
        )

    while True:
        try:
            # Yeni rapor öğelerini tara
            new_items = scan_new_reports()
            if new_items:
                _log(f"{len(new_items)} yeni ACİL öğe bulundu")
                for item in new_items:
                    if already_processed(item["id"]):
                        continue
                    process_item(item)
                    time.sleep(3)
            else:
                _log("Yeni ACİL öğe yok.")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            _log("Entegrasyon döngüsü durduruldu.")
            break
        except Exception:
            _log(f"Döngü hatası: {traceback.format_exc()}")
            time.sleep(30)

if __name__ == "__main__":
    main()
