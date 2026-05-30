"""
Kuroshin Otonom Ajan Döngüsü — FAZ 2
OODA: Uyan → Karar Ver → Görev Çalıştır → Değerlendir → Güncelle → Planla → Uyu
"""
import json
import re
import sys
import time
import datetime
import logging
import traceback
from pathlib import Path

sys.path.insert(0, "/mnt/c/Kuroshin")

import requests
from scripts.kuroshin_goals import (
    load_goals, load_tasks, add_task, update_task,
    update_goal, save_context, load_context, clear_context,
    hedef_ozeti, hedef_ilerleme_guncelle,
    gorev_gecmisi_guncelle, gorev_gecmisi_yukle, dongu_kirici_kontrol,
    _arastirma_kalite_kontrol, sorgu_deneme_sifirla,
)
from scripts.kuroshin_telegram_ajan import (
    send_task_start, send_task_progress,
    send_task_complete, send_task_blocked,
    ajan_dur_mu,
)

# ── SABITLER ──────────────────────────────────────────
BASE_DIR     = Path("/mnt/c/Kuroshin")
MEMORY_DIR   = BASE_DIR / "memory"
NEXT_WAKEUP  = MEMORY_DIR / "next_wakeup.json"
REFLECT_DIR  = MEMORY_DIR / "reflections"
LOG_FILE     = BASE_DIR / "logs" / "autonomous.log"

# ── E-05 (29 May 2026): REFLEXION VERBAL BUFFER (Shinn et al. arXiv 2303.11366) ───
#   Başarısız görev → verbal critique → bir sonraki karar promptuna inject.
#   Episodic buffer pattern: hata tarihçesinden öğren, model ağırlığını değiştirmeden.
REFLEXION_BUFFER = MEMORY_DIR / "reflexion_buffer.json"
_REFLEXION_MAX_PER_GOAL = 5     # her hedef için max kayıt (eskileri rotate)
_REFLEXION_INJECT_COUNT = 3     # karar promptuna kaç tanesi inject edilsin

LLAMA_URL         = "http://localhost:8080/v1/chat/completions"
WALKER_URL        = "http://localhost:9002/task"
COUNCIL_URL       = "http://localhost:9004/task"
CHROMA_URL        = "http://localhost:8100"
LLAMA_MODEL       = "kuroshin"
INTERNAL_TOOL_URL = "http://127.0.0.1:8201"  # F5-01: chancellor internal tool server

MAX_ADIM_PER_SESSION = 10  # sonsuz döngü önleme (5→10: DOOM pipeline için yeterli)
MAX_GOREV_PER_OTURUM = 3   # tek oturumda max görev

# ── TOKEN BÜTÇESİ (AJAN-10) ──────────────────────────────
_TB_MAX_LLM_CALLS = 10   # oturum başına max LLM çağrısı (karar×3 + reflect×3 + plan×3 + ekstra)
_TB_OTURUM: dict  = {"cagri_sayisi": 0}

# ── SEMANTİK DEDUP (AJAN-10) ─────────────────────────────
_SD_TTL        = 7200        # saniye: 2 saat cache (process restart'ı aşar)
_SD_CACHE_FILE = MEMORY_DIR / "sd_cache.json"
_SD_CACHE: dict = {}         # {sorgu_norm: {"ts": float, "sonuc": str}}
_SD_ESIK  = 0.70             # Jaccard benzerlik eşiği

def _sd_cache_yukle():
    """Disk'ten SD cache'i yükle — process restart'ta kayıp önlenir."""
    global _SD_CACHE
    try:
        if _SD_CACHE_FILE.exists():
            raw = json.loads(_SD_CACHE_FILE.read_text(encoding="utf-8"))
            simdi = time.time()
            _SD_CACHE = {k: v for k, v in raw.items() if simdi - v["ts"] < _SD_TTL}
    except Exception:
        _SD_CACHE = {}

def _sd_cache_kaydet_disk():
    """SD cache'i diske yaz."""
    try:
        _SD_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SD_CACHE_FILE.write_text(json.dumps(_SD_CACHE, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

_sd_cache_yukle()  # Modül yüklenince diskten oku

# ── CIRCUIT BREAKER (AJAN-09) ──────────────────────────
# Sessiz timeout döngüsünü önler: N×hata → OPEN → bypass → 60s → HALF-OPEN → test
_CB_MAX_FAILURE = 3      # kaç timeout'ta OPEN'a geç
_CB_COOLDOWN    = 60     # saniye: OPEN → HALF-OPEN
_CB_SERVICES: dict = {} # {servis: {"durum": "closed"|"open"|"half-open", "hata": N, "son_hata_ts": float}}
_CB_SERVIS_MAP = {       # araç adı → circuit breaker servis adı
    "walker_research":   "walker",
    "web_search":        "council_gozcu",
    "council_gozcu":     "council_gozcu",
    "council_teknisyen": "council_teknisyen",
}

def _cb_durum(servis: str) -> str:
    """Circuit durum döndür; OPEN ise cooldown bittiyse HALF-OPEN'a geç."""
    cb = _CB_SERVICES.setdefault(servis, {"durum": "closed", "hata": 0, "son_hata_ts": 0.0})
    if cb["durum"] == "open" and time.time() - cb["son_hata_ts"] >= _CB_COOLDOWN:
        cb["durum"] = "half-open"
        _log.info(f"[CIRCUIT] {servis} HALF-OPEN — kurtarma testi başlıyor")
    return cb["durum"]

def _cb_hata(servis: str):
    """Servis hatası kaydet; eşik aşılırsa OPEN'a al ve Telegram'a bildir."""
    cb = _CB_SERVICES.setdefault(servis, {"durum": "closed", "hata": 0, "son_hata_ts": 0.0})
    cb["hata"] += 1
    cb["son_hata_ts"] = time.time()
    if cb["durum"] == "half-open" or cb["hata"] >= _CB_MAX_FAILURE:
        cb["durum"] = "open"
        msg = f"⚡ [CIRCUIT] {servis} OPEN ({cb['hata']}× timeout) — {_CB_COOLDOWN}s bypass"
        _log.warning(msg)
        _telegram(f"<b>⚡ Circuit Breaker Devreye Girdi</b>\n{msg}")

def _cb_basari(servis: str):
    """Başarılı çağrı: HALF-OPEN → CLOSED, hata sayacı sıfırla."""
    prev = _CB_SERVICES.get(servis, {}).get("durum", "closed")
    _CB_SERVICES[servis] = {"durum": "closed", "hata": 0, "son_hata_ts": 0.0}
    if prev == "half-open":
        _log.info(f"[CIRCUIT] {servis} CLOSED — servis kurtarıldı")

def _cb_sonuc_hata_mi(sonuc: str) -> bool:
    """Araç sonucu gerçek bir hata/timeout mu? → CB hata sayacı artır."""
    if not sonuc or len(sonuc.strip()) < 5:
        return True
    s = sonuc.lower()
    return (
        sonuc.startswith("❌") or
        sonuc.startswith("⚡ [CIRCUIT]") or
        "timed out" in s or
        "zaman aşımı" in s or
        "walker hatası" in s or
        "gözcü hatası" in s or
        "teknisyen hatası" in s or
        ("hata" in s and len(sonuc) < 80)
    )

# ── LOGGING ───────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
import logging.handlers as _log_handlers
try:
    _handler = _log_handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
except Exception:
    _handler = logging.FileHandler(LOG_FILE, encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_handler, logging.StreamHandler()],
)
_log = logging.getLogger("autonomous")


def _simdi() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ── TELEGRAM BİLDİRİM ────────────────────────────────
def _telegram(mesaj: str):
    """Genel amaçlı kısa bildirim. Kritik adım bildirimleri kuroshin_telegram_ajan'dan gelir."""
    try:
        from dotenv import load_dotenv
        import os as _os
        load_dotenv(BASE_DIR / ".env")
        token   = _os.getenv("TELEGRAM_TOKEN", "")
        chat_id = _os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mesaj, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        _log.warning(f"[TG] Bildirim gönderilemedi: {e}")


def _chat_id() -> str:
    """Aktif Telegram chat ID'sini döndür."""
    try:
        from dotenv import load_dotenv
        import os as _os2
        load_dotenv(BASE_DIR / ".env")
        return _os2.getenv("TELEGRAM_CHAT_ID", "")
    except Exception:
        return ""


# ── LLM ÇAĞRISI ───────────────────────────────────────
def _llm_cagir(prompt: str, max_tokens: int = 512,
               temperature: float = 0.3) -> str:
    """llama-server'a HTTP istek at, ham metin döndür.
    AJAN-10: Token bütçesi — oturum başına max _TB_MAX_LLM_CALLS çağrı.
    """
    _TB_OTURUM["cagri_sayisi"] += 1
    if _TB_OTURUM["cagri_sayisi"] > _TB_MAX_LLM_CALLS:
        mesaj = (f"⛔ [TOKEN-BÜTÇE] Oturum limiti aşıldı "
                 f"({_TB_OTURUM['cagri_sayisi']}/{_TB_MAX_LLM_CALLS}) — LLM çağrısı engellendi")
        _log.warning(mesaj)
        _telegram(mesaj)
        return ""
    _log.debug(f"[LLM] Çağrı {_TB_OTURUM['cagri_sayisi']}/{_TB_MAX_LLM_CALLS} "
               f"| max_tokens={max_tokens}")
    try:
        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }, timeout=120)
        r.raise_for_status()
        choices = r.json().get("choices", [])
        if not choices:
            _log.warning("[LLM] Boş choices listesi")
            return ""
        return (choices[0].get("message", {}).get("content") or "").strip()
    except Exception as e:
        _log.error(f"[LLM] Çağrı hatası: {e}")
        return ""


def _sd_jaccard(a: str, b: str) -> float:
    """İki sorgu arasındaki Jaccard kelime benzerliği (0.0-1.0)."""
    ka = set(a.lower().split())
    kb = set(b.lower().split())
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / len(ka | kb)


def _sd_cache_kontrol(sorgu: str) -> str | None:
    """
    AJAN-10 Semantik Dedup: Son 30 dk içinde benzer sorgu yapıldıysa
    cache sonucunu döndür, yoksa None döndür.
    """
    simdi = time.time()
    sorgu_norm = sorgu.strip().lower()
    for k, v in list(_SD_CACHE.items()):
        if simdi - v["ts"] > _SD_TTL:
            del _SD_CACHE[k]
            continue
        benzerlik = _sd_jaccard(sorgu_norm, k)
        if benzerlik >= _SD_ESIK:
            _log.info(f"[SD] Cache hit — benzerlik={benzerlik:.2f} | sorgu='{sorgu[:60]}'")
            return f"[SD-CACHE {benzerlik:.0%}] {v['sonuc']}"
    return None


def _sd_cache_kaydet(sorgu: str, sonuc: str):
    """Araştırma sonucunu semantik dedup cache'ine ekle ve diske kaydet."""
    _SD_CACHE[sorgu.strip().lower()] = {"ts": time.time(), "sonuc": sonuc}
    _sd_cache_kaydet_disk()


def _strip_think(metin: str) -> str:
    """<think>...</think> bloklarını ve fazla boşlukları temizle."""
    metin = re.sub(r"<think>.*?</think>", "", metin, flags=re.DOTALL)
    return metin.strip()


# ── F2-03: KARAR JSON PARSE ───────────────────────────
def _parse_karar(json_str: str) -> dict | None:
    """
    Model çıktısından karar JSON'unu robust parse et.
    Think bloğu strip → markdown fence strip → json.loads.
    Döner: {"karar": "A"|"B"|"C", "task_id"?: ..., "sebep"?: ..., ...}
    Başarısızsa None döner.
    """
    temiz = _strip_think(json_str)
    # ```json ... ``` veya ``` ... ``` bloğu
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", temiz, re.DOTALL)
    if fence:
        temiz = fence.group(1)
    # Düz JSON objesi ara (greedy — truncated JSON'u da yakala)
    obj = re.search(r"\{.*\}", temiz, re.DOTALL)
    if obj:
        temiz = obj.group(0)
    try:
        return json.loads(temiz)
    except json.JSONDecodeError:
        # Truncated JSON fallback: "karar" ve "task_id" alanlarını regex ile çıkar
        karar_m    = re.search(r'"karar"\s*:\s*"([ABC])"', temiz)
        task_id_m  = re.search(r'"task_id"\s*:\s*"([^"]+)"', temiz)
        bekle_m    = re.search(r'"bekle_dakika"\s*:\s*(\d+)', temiz)
        if karar_m:
            sonuc: dict = {"karar": karar_m.group(1), "sebep": "truncated JSON — regex fallback"}
            if task_id_m:
                sonuc["task_id"] = task_id_m.group(1)
            if bekle_m:
                sonuc["bekle_dakika"] = int(bekle_m.group(1))
            _log.warning(f"[PARSE] Truncated JSON — regex fallback: karar={sonuc['karar']} task_id={sonuc.get('task_id')}")
            return sonuc
        _log.warning(f"[PARSE] JSON parse başarısız: {temiz[:200]}")
        return None


# ── F2-02: KARAR PROMPTU ──────────────────────────────
# ── E-05: REFLEXION BUFFER HELPER'LARI ───────────────────
def _load_reflexion_buffer() -> dict:
    """memory/reflexion_buffer.json oku. Format: {goal_id: [reflexion_record, ...]}"""
    if not REFLEXION_BUFFER.exists():
        return {}
    try:
        return json.loads(REFLEXION_BUFFER.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_reflexion(goal_id: str, task_id: str, sebep: str, yeniden_dene: str) -> None:
    """E-05: Başarısız görev sonrası verbal critique kaydet.

    sebep: NEDEN başarısız oldu (kısa, somut)
    yeniden_dene: GELECEKTE ne dene (somut alternatif)
    """
    if not goal_id:
        return
    buf = _load_reflexion_buffer()
    entry = {
        "task_id": task_id,
        "ts": datetime.datetime.now().isoformat()[:19],
        "sebep": sebep[:300],
        "yeniden_dene": yeniden_dene[:300],
    }
    lst = buf.get(goal_id, [])
    lst.append(entry)
    # Eski kayıtları rotate
    if len(lst) > _REFLEXION_MAX_PER_GOAL:
        lst = lst[-_REFLEXION_MAX_PER_GOAL:]
    buf[goal_id] = lst
    REFLEXION_BUFFER.parent.mkdir(parents=True, exist_ok=True)
    REFLEXION_BUFFER.write_text(json.dumps(buf, ensure_ascii=False, indent=2), encoding="utf-8")
    _log.info(f"[REFLEXION] {goal_id}/{task_id} kayıt: {sebep[:60]}...")


def _reflexion_promptu_satiri(goal_id: str) -> str:
    """E-05: İlgili hedef için son N reflexion'ı karar prompt satırı olarak döndür."""
    if not goal_id:
        return ""
    buf = _load_reflexion_buffer()
    lst = buf.get(goal_id, [])[-_REFLEXION_INJECT_COUNT:]
    if not lst:
        return ""
    out = ["GEÇMİŞ HATALAR — bu hedefte daha önce şunlar başarısız oldu, tekrar etme:"]
    for e in lst:
        out.append(f"  - [{e['task_id']}] {e['sebep']} → Öneri: {e['yeniden_dene']}")
    return "\n".join(out) + "\n\n"


def _karar_promptu(goals: list, tasks: list, ctx: dict) -> str:
    """
    Model için karar prompt'u üret.
    Context'e sadece 1 aktif görev + özet liste girer (16K tasarrufu).
    """
    goals_str = ""
    for g in goals[:5]:
        goals_str += (f"  [{g['id']}] {g['baslik']} — "
                      f"durum:{g['durum']} ilerleme:%{g['ilerleme']}\n")
    if not goals_str:
        goals_str = "  (Aktif hedef yok)\n"

    # CM-01: Karar promptuna sadece 1 görev gönder (16K tasarrufu)
    tasks_str = ""
    for t in tasks[:1]:
        adim_say = len(t.get("adimlar", []))
        tasks_str += (f"  [{t['id']}] {t['baslik']} — "
                      f"durum:{t['durum']} hedef:{t.get('goal_id','')} "
                      f"adım:{adim_say}\n")
    if tasks_str and len(tasks) > 1:
        tasks_str += f"  (+{len(tasks)-1} görev daha tasks.json'da)\n"
    elif not tasks_str:
        tasks_str = "  (Bekleyen görev yok)\n"

    ctx_str = ""
    if ctx.get("aktif_gorev_id"):
        ctx_str = (f"  Yarım kalan: {ctx['aktif_gorev_id']} "
                   f"(adım {ctx['tamamlanan_adim']} tamamlandı)\n"
                   f"  Not: {ctx.get('devam_notu', '')}\n")
    else:
        ctx_str = "  (Yarım kalan görev yok)\n"

    # E-05: Aktif görevin hedefine ait reflexion buffer'ı inject
    reflexion_str = ""
    if tasks:
        first_goal = tasks[0].get("goal_id", "")
        reflexion_str = _reflexion_promptu_satiri(first_goal)

    return f"""Sen Kuroshin'sin. Şu an otonom karar verme modundasın.

AKTİF HEDEFLER:
{goals_str}
BEKLEYEN/AKTİF GÖREVLER:
{tasks_str}
YARIM KALAN BAĞLAM:
{ctx_str}
{reflexion_str}Şimdi sana 3 seçenek var:
A) Bekleyen bir göreve devam et veya yarım kalanı tamamla → task_id seç
B) Yeni bir görev başlat → goal_id ve baslik belirle
C) Bekle → sebep yaz, kaç dakika sonra tekrar kontrol et

Kararını SADECE JSON olarak ver, başka hiçbir şey yazma:
{{"karar": "A", "task_id": "T-001", "sebep": "En yüksek öncelikli bekleyen görev"}}
veya
{{"karar": "B", "goal_id": "G-001", "baslik": "Yeni görev açıklaması", "sebep": "..."}}
veya
{{"karar": "C", "bekle_dakika": 120, "sebep": "Şu an yapılacak görev yok"}}"""


# ── F2-04: TEK ARAÇ ADIMI ─────────────────────────────
def _gorev_adim_calistir(adim: dict) -> str:
    """
    Tek araç adımını çalıştır.
    F5-01: Önce chancellor internal tool server (port 8201) dene — tüm araçlar ve güvenlik katmanı dahil.
    Fallback: Kritik araçlar için direkt HTTP (walker, council, reddit_read).
    """
    arac  = adim.get("arac", "")
    param = adim.get("parametre", {})
    _log.info(f"[ADIM] Araç: {arac} | param: {str(param)[:80]}")

    # ── CIRCUIT BREAKER BYPASS ────────────────────────
    if arac in _CB_SERVIS_MAP:
        _servis_cb = _CB_SERVIS_MAP[arac]
        if _cb_durum(_servis_cb) == "open":
            bypass_msg = f"⚡ [CIRCUIT] {_servis_cb} OPEN — bypass ({_CB_COOLDOWN}s sonra denenir)"
            _log.warning(bypass_msg)
            return bypass_msg

    # ── SEMANTİK DEDUP (AJAN-10) ─────────────────────
    _SD_ARACLARI = {"walker_research", "web_search", "council_gozcu", "reddit_read"}
    if arac in _SD_ARACLARI:
        _sd_sorgu = str(param.get("task", param.get("sorgu", param.get("query", ""))))
        if _sd_sorgu:
            _cached = _sd_cache_kontrol(_sd_sorgu)
            if _cached is not None:
                return _cached

    # F6-06: md_guncelle dahili komutu — kuroshin_md_agent üzerinden
    if arac == "md_guncelle":
        try:
            from scripts.kuroshin_md_agent import md_guncelle as _md_g
            sonuc = _md_g(
                dosya_yolu = param.get("dosya", ""),
                bolum      = param.get("bolum", ""),
                yeni_icerik= param.get("icerik", ""),
                tur        = param.get("tur", "bulgu_ekle"),
            )
            if sonuc["ok"]:
                return f"✅ MD güncellendi: {Path(param.get('dosya','')).name}"
            return f"⏳ MD: {sonuc['durum']}"
        except Exception as e:
            return f"❌ md_guncelle hatası: {e}"

    # write_file: Chancellor parametrelerini (path/content) tanımayabilir; direkt yaz
    if arac == "write_file":
        try:
            yol    = Path(param.get("yol", param.get("path", "")))
            icerik = param.get("icerik", param.get("content", ""))
            if not yol or not str(yol).startswith("/mnt/c/Kuroshin"):
                return f"❌ write_file: güvensiz yol: {yol}"
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_text(icerik, encoding="utf-8")
            return f"✅ Dosya yazıldı: {yol} ({len(icerik)} kar)"
        except Exception as e:
            return f"❌ write_file hatası: {e}"

    # F5-01: Internal tool server üzerinden chancellor.run_tool() çağır
    # Ağır araçlar için timeout artırıldı; ReadTimeout'da double-call yapılmaz
    _agir = arac in ("walker_research", "council_gozcu", "council_teknisyen", "fetch_page_deep", "web_search")
    _f501_timeout = 360 if _agir else 120
    try:
        r = requests.post(
            f"{INTERNAL_TOOL_URL}/run_tool",
            json={"name": arac, "args": param},
            timeout=_f501_timeout,
        )
        if r.status_code == 200:
            _r_txt = r.json().get("result", f"[{arac}] boş döndü.")
            if not _r_txt.startswith("Bilinmeyen araç"):
                return _r_txt
            _log.warning(f"[F5-01] {arac} chancellor'da tanımsız — fallback aktif")
            # fall through to direct fallback below
        else:
            _log.warning(f"[F5-01] Internal server HTTP {r.status_code} — fallback'e geçiliyor")
    except requests.exceptions.ConnectionError:
        _log.warning(f"[F5-01] Internal server kapalı (port 8201) — direkt fallback")
    except requests.exceptions.ReadTimeout:
        # ReadTimeout: istek gönderildi ama yanıt gelmedi — double-call yapma
        _log.warning(f"[F5-01] {arac} timeout ({_f501_timeout}s) — zaman aşımı, fallback yok")
        return f"❌ {arac} zaman aşımı ({_f501_timeout}s) — servis meşgul veya yavaş"
    except Exception as e:
        _log.warning(f"[F5-01] Internal server hatası: {e} — fallback")

    # ── FALLBACK: Chancellor kapalıyken direkt HTTP ────
    try:
        if arac == "walker_research":
            r = requests.post(WALKER_URL, json={"task": param.get("task", str(param))},
                              timeout=360)
            return r.json().get("result", "Walker boş döndü.") if r.status_code == 200 \
                else f"Walker HTTP {r.status_code}"

        elif arac in ("web_search", "council_search"):
            r = requests.post(COUNCIL_URL,
                              json={"agent": "gozcu", "task": param.get("task", str(param))},
                              timeout=360)
            return r.json().get("result", "Gözcü boş döndü.") if r.status_code == 200 \
                else f"Gözcü HTTP {r.status_code}"

        elif arac == "reddit_read":
            sub   = param.get("subreddit", "LocalLLaMA")
            sort  = param.get("sort", "hot")
            limit = param.get("limit", 5)
            url   = f"https://www.reddit.com/r/{sub}/{sort}.json?limit={limit}"
            r = requests.get(url, headers={"User-Agent": "Kuroshin/1.0"}, timeout=30)
            if r.status_code != 200:
                return f"Reddit HTTP {r.status_code}"
            posts = r.json().get("data", {}).get("children", [])
            satirlar = [f"r/{sub} — {sort} ({len(posts)} post)"]
            for p in posts:
                d = p["data"]
                satirlar.append(f"  [{d['id']}] {d['title'][:80]} (↑{d['score']})")
            return "\n".join(satirlar)

        elif arac == "write_file":
            yol    = Path(param.get("yol", param.get("path", "")))
            icerik = param.get("icerik", param.get("content", ""))
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_text(icerik, encoding="utf-8")
            return f"✅ Dosya yazıldı: {yol}"

        elif arac == "council_gozcu":
            r = requests.post(COUNCIL_URL,
                              json={"agent": "gozcu",
                                    "task": param.get("task", str(param))},
                              timeout=360)
            return r.json().get("result", "Gözcü boş döndü.") \
                if r.status_code == 200 else f"Gözcü HTTP {r.status_code}"

        elif arac == "council_teknisyen":
            r = requests.post(COUNCIL_URL,
                              json={"agent": "teknisyen",
                                    "task": param.get("task", str(param))},
                              timeout=360)
            return r.json().get("result", "Teknisyen boş döndü.") \
                if r.status_code == 200 else f"Teknisyen HTTP {r.status_code}"

        elif arac == "list_dir":
            try:
                yol_ld = Path(param.get("path", "/mnt/c/Kuroshin"))
                ogeler = sorted(yol_ld.iterdir())[:40]
                satirlar = [f"{yol_ld} ({len(ogeler)} öge):"]
                for e in ogeler:
                    satirlar.append(f"  {'📁' if e.is_dir() else '📄'} {e.name}")
                return "\n".join(satirlar)
            except Exception as e_ld:
                return f"list_dir hata: {e_ld}"

        elif arac == "read_file":
            try:
                yol_rf = Path(param.get("path", ""))
                return yol_rf.read_text(encoding="utf-8", errors="replace")[:3000]
            except Exception as e_rf:
                return f"read_file hata: {e_rf}"

        elif arac == "fetch_page_deep":
            try:
                url_fp = param.get("url", "")
                r = requests.get(url_fp,
                                 headers={"User-Agent": "Kuroshin/1.0"},
                                 timeout=30)
                text_fp = r.text[:4000] if r.status_code == 200 \
                    else f"fetch_page HTTP {r.status_code}"
                return text_fp
            except Exception as e_fp:
                return f"fetch_page_deep hata: {e_fp}"

        elif arac in ("chroma_query", "chroma_search"):
            try:
                sorgu_cq = param.get("sorgu", param.get("query",
                                     param.get("task", str(param))))
                r = requests.post(f"{CHROMA_URL}/query",
                                  json={"collection": "kuroshin_memory",
                                        "query": sorgu_cq, "n_results": 3},
                                  timeout=15)
                return r.json().get("result", "ChromaDB boş döndü.") \
                    if r.status_code == 200 else f"ChromaDB HTTP {r.status_code}"
            except Exception as e_cq:
                return f"chroma_query hata (servis kapalı?): {e_cq}"

        elif arac == "chroma_add":
            try:
                icerik_ca = param.get("icerik", param.get("content", str(param)))
                col_ca    = param.get("collection", "kuroshin_memory")
                import time as _tca
                uid = f"doom_{int(_tca.time()) % 10000000}"
                r = requests.post(f"{CHROMA_URL}/add",
                                  json={"collection": col_ca,
                                        "documents": [icerik_ca],
                                        "ids": [uid]},
                                  timeout=15)
                return f"✅ ChromaDB'ye eklendi (id: {uid})" \
                    if r.status_code == 200 else f"ChromaDB add HTTP {r.status_code}"
            except Exception as e_ca:
                return f"chroma_add hata (servis kapalı?): {e_ca}"

        else:
            return f"⚠️ Araç {arac}: internal server kapalı, fallback yok."

    except requests.exceptions.ConnectionError as e:
        return f"❌ Bağlantı hatası ({arac}): {e}"
    except Exception as e:
        _log.error(f"[ADIM] Hata: {e}\n{traceback.format_exc()}")
        return f"❌ Araç hatası ({arac}): {e}"


# ── F2-05: REFLECTION PROMPTU ─────────────────────────
# ── E-06: PLAN-AND-EXECUTE — Dinamik plan üretici (arXiv 2503.09572 analog) ──────
def _plan_uret(task: dict, n_target: int = 5) -> list | None:
    """E-06: Görev adımı yoksa veya plan_mode=='dynamic' ise model'den somut araç
    zinciri planı al. JSON list döner, başarısız parse ise None.
    Token bütçe sayacına 1 ekler (AJAN-10 ile uyumlu).
    """
    prompt = f"""Sen Kuroshin'sin. Şu görevi maksimum {n_target} adımlı somut bir araç zincirine böl.

GÖREV: {task.get("baslik", "")}
HEDEF: {task.get("goal_id", "")}

Sadece JSON liste döndür, başka hiçbir şey yazma. Örnek format:
[
  {{"sirano":1, "arac":"walker_research", "parametre":{{"task":"X araştır"}}}},
  {{"sirano":2, "arac":"chroma_search",   "parametre":{{"sorgu":"X özet"}}}},
  {{"sirano":3, "arac":"write_file",      "parametre":{{"path":"X.md", "content":"..."}}}}
]

Kullanılabilir araçlar: walker_research, web_search, chroma_search, chroma_add,
read_file, write_file, system_command, md_guncelle, reddit_read."""
    cikti = _llm_cagir(prompt, max_tokens=600, temperature=0.2)
    # Önce ham JSON list extract
    try:
        m = re.search(r'\[\s*\{.*?\}\s*\]', cikti, re.DOTALL)
        if m:
            plan = json.loads(m.group(0))
            if isinstance(plan, list) and plan:
                # Sıralama ve eksik alan kontrolü
                for i, adim in enumerate(plan):
                    adim.setdefault("sirano", i + 1)
                    adim.setdefault("durum", "bekliyor")
                _log.info(f"[E-06 Plan-and-Execute] {task.get('id','?')} → {len(plan)} adım üretildi")
                return plan
    except Exception as _ep:
        _log.warning(f"[E-06] Plan parse hatası: {_ep}")
    _log.warning(f"[E-06] {task.get('id','?')} için plan üretilemedi (LLM yanıtı: {cikti[:100]})")
    return None


def _reflection_promptu(task: dict, sonuc: str) -> str:
    adimlar_str = ""
    for a in task.get("adimlar", []):
        adimlar_str += f"  Adım {a['sirano']}: {a['arac']} — {a.get('durum','?')}\n"

    return f"""Kuroshin olarak az önce tamamladığın görevi değerlendir.

GÖREV: {task.get('baslik', '')}
HEDEF ID: {task.get('goal_id', '')}
ADIMLAR:
{adimlar_str}
SONUÇ:
{sonuc[:1000]}

Şu soruları yanıtla (SADECE JSON):
{{
  "basarili": true veya false,
  "kalite_skoru": 0.0-1.0,
  "eksik": "Eksik olan varsa açıkla, yoksa boş bırak",
  "ders": "Bu görevden öğrenilen en önemli şey",
  "sonraki_oneri": "Bir sonraki mantıksal adım ne olmalı"
}}"""


class KuroshinAjan:
    """
    Otonom ajan ana sınıfı.
    Tek oturumda en fazla MAX_GOREV_PER_OTURUM görev çalıştırır.
    """

    def __init__(self):
        self.goals:   list = []
        self.tasks:   list = []
        self.ctx:     dict = {}
        self.oturum_gorev_sayisi = 0

    # ── [1] UYAN ──────────────────────────────────────
    def uyan(self):
        """Goals, tasks, context yükle. Telegram'a uyanış bildirimi."""
        # AJAN-10: Her oturum başında token bütçe sayacı ve SD cache sıfırla
        _TB_OTURUM["cagri_sayisi"] = 0
        _SD_CACHE.clear()
        _log.info(f"[AJAN-10] Token bütçe sıfırlandı (max={_TB_MAX_LLM_CALLS}) | SD cache temizlendi")

        self.goals = load_goals(durum="aktif")
        self.tasks = load_tasks(durum="bekliyor") + load_tasks(durum="aktif")
        self.ctx   = load_context()
        _log.info(f"[UYAN] Hedef: {len(self.goals)} | Görev: {len(self.tasks)} | "
                  f"Bağlam: {self.ctx.get('aktif_gorev_id', 'yok')}")
        _telegram(
            f"🤖 <b>Kuroshin Ajan Uyandı</b>\n"
            f"Aktif hedef: {len(self.goals)} | Bekleyen görev: {len(self.tasks)}\n"
            f"Yarım kalan: {self.ctx.get('aktif_gorev_id', 'yok')}"
        )

    # ── [2] KARAR VER ─────────────────────────────────
    def karar_ver(self) -> dict | None:
        """
        Model'e karar prompt'u gönder, JSON parse et.
        Döner: {"karar": "A"|"B"|"C", ...} veya None (başarısız parse)
        """
        if not self.goals and not self.tasks and not self.ctx.get("aktif_gorev_id"):
            _log.info("[KARAR] Hedef/görev yok — C kararı üretiliyor.")
            return {"karar": "C", "bekle_dakika": 60, "sebep": "Hedef/görev listesi boş"}

        # CM-02: Karar promptu için sadece 1 aktif/bekleyen görev yükle
        _karar_tasks = load_tasks(durum="aktif", limit=1)
        if not _karar_tasks:
            _karar_tasks = load_tasks(durum="bekliyor", limit=1)
        prompt  = _karar_promptu(self.goals, _karar_tasks, self.ctx)
        cikti   = _llm_cagir(prompt, max_tokens=512, temperature=0.2)
        _log.info(f"[KARAR] Model çıktısı: {cikti[:200]}")
        karar   = _parse_karar(cikti)

        if karar is None:
            # Retry: daha basit prompt ile bir kez daha dene
            _log.warning("[KARAR] JSON parse başarısız — retry (basit prompt).")
            _tid = _karar_tasks[0]["id"] if _karar_tasks else "?"
            _retry_prompt = (
                f'Sadece JSON yaz, başka hiçbir şey yazma:\n'
                f'{{"karar": "A", "task_id": "{_tid}", "sebep": "bekleyen görev"}}'
                f'\nYa da beklemek istersen:\n'
                f'{{"karar": "C", "bekle_dakika": 60, "sebep": "şu an uygun değil"}}'
            )
            _retry_cikti = _llm_cagir(_retry_prompt, max_tokens=100, temperature=0.1)
            _log.info(f"[KARAR] Retry çıktısı: {_retry_cikti[:100]}")
            karar = _parse_karar(_retry_cikti)

        if karar is None:
            _log.warning("[KARAR] Retry da başarısız, varsayılan C döndürülüyor.")
            return {"karar": "C", "bekle_dakika": 30,
                    "sebep": "Model yanıtı parse edilemedi"}

        # F4-04: Döngü kırıcı — model aynı görevi son 3 içinde seçtiyse reddet
        if karar.get("karar") == "A":
            tid = karar.get("task_id", "")
            if tid and dongu_kirici_kontrol(tid, son_n=3):
                _log.warning(f"[F4-04] Döngü kırıcı devreye girdi: {tid} son 3'te var.")
                # Başka bekleyen görev var mı?
                alternatif = [
                    t for t in self.tasks
                    if t["id"] != tid and t.get("durum") == "bekliyor"
                ]
                if alternatif:
                    karar["task_id"] = alternatif[0]["id"]
                    karar["sebep"]   = f"Döngü kırıcı: {tid} yerine {alternatif[0]['id']}"
                    _log.info(f"[F4-04] Alternatif seçildi: {alternatif[0]['id']}")
                else:
                    return {"karar": "C", "bekle_dakika": 60,
                            "sebep": f"Döngü kırıcı: {tid} tekrar seçildi, beklenecek"}

        return karar

    # ── [3] GÖREV ÇALIŞTIR ────────────────────────────
    def gorev_calistir(self, task: dict) -> str:
        """
        Adım adım araç zinciri çalıştır.
        Her adımda bağlamı task_context.json'a yaz (bağlam köprüsü — F2-06).
        MAX_ADIM_PER_SESSION sınırı geçilirse durur.
        E-06: Adım yoksa veya plan_mode=='dynamic' ise Plan-and-Execute ile dinamik plan üret.
        """
        task_id = task["id"]
        adimlar = task.get("adimlar", [])
        # E-06: Plan-and-Execute hibrit — adim yoksa veya dinamik istek varsa LLM'den plan
        if (not adimlar) or task.get("plan_mode") == "dynamic":
            plan = _plan_uret(task)
            if plan:
                adimlar = plan
                task["adimlar"] = plan  # in-memory inject
                # tasks.json'a da yansıt (kalıcı)
                try:
                    update_task(task_id, durum="aktif", sonuc="", hata="")
                except Exception:
                    pass
        update_task(task_id, durum="aktif")
        cid = _chat_id()
        send_task_start(cid, task)

        ara_sonuclar = {}
        tum_sonuc    = []
        adim_sayaci  = 0

        # Yarım kalan bağlam varsa kaldığı adımdan devam et — F2-06
        baslangic_adim = 0
        if self.ctx.get("aktif_gorev_id") == task_id:
            baslangic_adim = self.ctx.get("tamamlanan_adim", 0)
            ara_sonuclar   = self.ctx.get("ara_sonuclar", {})
            _log.info(f"[DEVAM] {task_id} → adım {baslangic_adim}'den devam")

        for i, adim in enumerate(adimlar):
            if i < baslangic_adim:
                continue
            # F4-05: Dışarı yazma araçları onay kapısı (HITL)
            _ONAY_GEREKEN = {"github", "reddit_tool"}
            if adim.get("arac") in _ONAY_GEREKEN:
                _log.info(f"[F4-05] Onay gerektiren araç: {adim['arac']} — bloke")
                update_task(task_id, durum="bloke",
                            hata=f"Onay bekleniyor: {adim['arac']}")
                send_task_blocked(cid, task,
                                  sebep=f"{adim['arac']} çalıştırmak için onay gerekli",
                                  onay_gerektiren=True)
                save_context(task_id, i, ara_sonuclar,
                             f"Onay bekleniyor — {adim['arac']} adım {i+1}")
                return "\n".join(tum_sonuc) + f"\n[ONAY BEKLENİYOR: {adim['arac']}]"

            # F3-06 /durdur sinyalini kontrol et
            if ajan_dur_mu():
                _log.info(f"[DUR] Kullanıcı durdurdu — {task_id} adım {i}")
                save_context(task_id, i, ara_sonuclar, "Kullanıcı tarafından durduruldu")
                send_task_blocked(cid, task, "Kullanıcı /durdur komutu verdi")
                return "\n".join(tum_sonuc) + "\n[KULLANICI DURDURDU]"

            if adim_sayaci >= MAX_ADIM_PER_SESSION:
                _log.warning(f"[LIMIT] Max adım ({MAX_ADIM_PER_SESSION}) aşıldı.")
                save_context(task_id, i, ara_sonuclar, "Adım limiti — yarıda kaldı")
                send_task_blocked(cid, task, f"Adım limiti ({MAX_ADIM_PER_SESSION}) aşıldı")
                return "\n".join(tum_sonuc) + "\n[ADIM LİMİTİ]"

            send_task_progress(cid, task, i + 1, len(adimlar), adim["arac"], "calisiyor")
            t0     = time.time()
            cikti  = _gorev_adim_calistir(adim)
            sure   = round(time.time() - t0, 1)

            # ── SEMANTİK DEDUP CACHE KAYDI (AJAN-10) ─────
            _sd_arac = adim.get("arac", "")
            if _sd_arac in {"walker_research", "web_search", "council_gozcu", "reddit_read"}:
                _sd_sorgu_k = str(adim.get("parametre", {}).get(
                    "task", adim.get("parametre", {}).get("sorgu", "")))
                if _sd_sorgu_k and cikti and not cikti.startswith("[SD-CACHE"):
                    _sd_cache_kaydet(_sd_sorgu_k, cikti)

            # ── CIRCUIT BREAKER SONUÇ KAYDI ──────────────
            _arac_cb = adim.get("arac", "")
            if _arac_cb in _CB_SERVIS_MAP:
                _sv = _CB_SERVIS_MAP[_arac_cb]
                if _cb_sonuc_hata_mi(cikti):
                    _cb_hata(_sv)
                else:
                    _cb_basari(_sv)

            # F6-01: Araştırma araçlarında KAY-03 / KAY-07 kalite kontrolü
            _ARASTIRMA_ARACLARI = {"walker_research", "web_search", "reddit_read", "chroma_search"}
            if adim.get("arac") in _ARASTIRMA_ARACLARI:
                _param = adim.get("parametre", {})
                _sorgu = str(_param.get("task", _param.get("sorgu", "")))
                _kalite = _arastirma_kalite_kontrol(cikti, sorgu=_sorgu)
                if not _kalite["gecti"]:
                    sebep = _kalite.get("sebep", "")
                    _log.warning(f"[KAY] Kalite kontrolü başarısız ({sebep}): {_kalite['detay']}")
                    if sebep == "limit_asti":
                        # KAY-07: 3 denemeden fazla → adımı "eksik" işaretle, devam et
                        cikti = f"[KAY-07 LIMIT] {_kalite['detay']}"
                    else:
                        # KAY-03: kısa sonuç → adımı atla, bir sonraki adıma geç
                        send_task_progress(cid, task, i + 1, len(adimlar),
                                           adim["arac"], "hata", sure)
                        continue  # bu adımı sayma, bir sonrakine geç

            # CM-03: Araştırma çıktısını ChromaDB'ye tam yaz
            if adim.get("arac") in {"walker_research", "web_search", "council_gozcu"}:
                _cm3_q = str(adim.get("parametre", {}).get(
                    "task", adim.get("parametre", {}).get("sorgu",
                    adim.get("parametre", {}).get("query", ""))))
                try:
                    _gorev_adim_calistir({
                        "arac": "chroma_add",
                        "parametre": {
                            "icerik": f"[AJAN-ARAŞTIRMA] {_cm3_q[:100]}\n{cikti}",
                            "collection": "kuroshin_memory",
                        },
                    })
                    _log.info(f"[CM-03] Araştırma ChromaDB'ye yazıldı: {_cm3_q[:60]}")
                except Exception as _cm3_e:
                    _log.warning(f"[CM-03] ChromaDB kayıt hatası: {_cm3_e}")

            adim["durum"] = "tamamlandi"
            update_task(task_id, adim_index=i, adim_durum="tamamlandi")
            ara_sonuclar[f"adim_{i+1}_cikti"] = cikti[:500]
            tum_sonuc.append(f"[Adım {i+1} — {adim['arac']}]\n{cikti}")

            send_task_progress(cid, task, i + 1, len(adimlar),
                               adim["arac"], "tamamlandi", sure)

            # F2-06: Her adım sonrası bağlamı kaydet
            save_context(task_id, i + 1, ara_sonuclar,
                         f"Adım {i+1} tamamlandı, devam ediliyor")
            adim_sayaci += 1

        return "\n\n".join(tum_sonuc)

    # ── [4] DEĞERLENDİR ───────────────────────────────
    def degerlendir(self, task: dict, sonuc: str) -> dict:
        """
        Model reflection prompt'u çalıştır.
        Sonucu memory/reflections/ dizinine YYYY-MM-DD_T-XXX.md olarak yaz.
        """
        prompt      = _reflection_promptu(task, sonuc)
        cikti       = _llm_cagir(prompt, max_tokens=900, temperature=0.2)
        reflection  = _parse_karar(cikti) or {
            "basarili": True,
            "kalite_skoru": 0.5,
            "eksik": "",
            "ders": cikti[:200] if cikti else "Model yanıt vermedi",
            "sonraki_oneri": ""
        }

        # Reflection dosyasına yaz
        tarih = datetime.date.today().isoformat()
        rf    = REFLECT_DIR / f"{tarih}_{task['id']}.md"
        REFLECT_DIR.mkdir(parents=True, exist_ok=True)
        rf.write_text(
            f"# Reflection — {task['id']} ({tarih})\n\n"
            f"**Görev:** {task.get('baslik', '')}\n\n"
            f"**Kalite Skoru:** {reflection.get('kalite_skoru', '?')}\n\n"
            f"**Başarılı:** {reflection.get('basarili', '?')}\n\n"
            f"**Eksik:** {reflection.get('eksik', '')}\n\n"
            f"**Ders:** {reflection.get('ders', '')}\n\n"
            f"**Sonraki Öneri:** {reflection.get('sonraki_oneri', '')}\n",
            encoding="utf-8"
        )
        _log.info(f"[REFLECT] {rf.name} yazıldı. Kalite: {reflection.get('kalite_skoru')}")

        # E-05: Reflexion verbal buffer — başarısız görevler için
        if not reflection.get("basarili", True):
            _save_reflexion(
                goal_id      = task.get("goal_id", ""),
                task_id      = task["id"],
                sebep        = reflection.get("eksik", "") or reflection.get("ders", ""),
                yeniden_dene = reflection.get("sonraki_oneri", "")
            )
        return reflection

    # ── [5] GÜNCELLE ──────────────────────────────────
    def guncelle(self, task: dict, sonuc: str, reflection: dict):
        """tasks.json ve goals.json güncelle. F4-03: ilerleme hesabı. F4-04: geçmiş kaydet."""
        basarili = reflection.get("basarili", True)
        update_task(
            task["id"],
            durum  = "tamamlandi" if basarili else "bloke",
            sonuc  = sonuc[:500],
            hata   = reflection.get("eksik", "") if not basarili else ""
        )
        # F4-03: Hedef ilerleme hesabı — merkezi fonksiyon
        goal_id = task.get("goal_id", "")
        if goal_id:
            yuzde = hedef_ilerleme_guncelle(goal_id)
            _log.info(f"[F4-03] Hedef {goal_id} ilerleme: %{yuzde}")

        # F4-04: Geçmiş güncelle — döngü kırıcı için
        if basarili:
            gorev_gecmisi_guncelle(task["id"])

        clear_context()
        _log.info(f"[GUNCELLE] {task['id']} → {'tamamlandi' if basarili else 'bloke'}")

    # ── [6] PLANLA SONRAKİ — F4-01 ───────────────────
    def planla_sonraki(self, tamamlanan: dict, reflection: dict) -> dict:
        """
        F4-01: Gelişmiş planlama prompt'u.
        Geçmiş görevleri, hedef önceliklerini ve zaman farkındalığını kullanır.
        """
        goals_guncel  = load_goals(durum="aktif")
        tasks_guncel  = load_tasks(durum="bekliyor")
        gecmis        = gorev_gecmisi_yukle()
        saat          = datetime.datetime.now().hour

        # Zaman bağlamı
        if 8 <= saat < 12:
            zaman_notu = "Sabah — analitik görevler için iyi zaman."
        elif 12 <= saat < 17:
            zaman_notu = "Öğleden sonra — araştırma ve yazma uygun."
        elif 17 <= saat < 22:
            zaman_notu = "Akşam — topluluk etkileşimi (Reddit/GitHub) için uygun."
        else:
            zaman_notu = "Gece — hafif görevler, ağır araştırmadan kaçın."

        # Hedef öncelikleri
        goals_str = ""
        for g in sorted(goals_guncel, key=lambda x: x.get("oncelik", 99))[:4]:
            goals_str += (f"  [{g['id']}] {g['baslik'][:50]} "
                          f"— öncelik:{g.get('oncelik',3)} %{g.get('ilerleme',0)}\n")

        # Bekleyen görevler (döngü kırıcı: geçmiştekiler işaretli)
        tasks_str = ""
        for t in tasks_guncel[:5]:
            tekrar = " ⚠️(son 3'te)" if t["id"] in gecmis[-3:] else ""
            tasks_str += f"  [{t['id']}] {t['baslik'][:50]}{tekrar}\n"

        if not tasks_str:
            tasks_str = "  (Bekleyen görev yok)\n"

        prompt = f"""Kuroshin olarak bir sonraki görevi planla.

TAMAMLANAN:
  [{tamamlanan.get('id','')}] {tamamlanan.get('baslik','')}
  Kalite: {reflection.get('kalite_skoru','?')} | Öneri: {reflection.get('sonraki_oneri','')[:80]}

AKTİF HEDEFLER (öncelik sırasıyla):
{goals_str}
BEKLEYEN GÖREVLER:
{tasks_str}
SON {len(gecmis)} TAMAMLANAN: {', '.join(gecmis[-3:]) or 'yok'}

ZAMAN: {zaman_notu}

Karar:
- ⚠️ işaretli görevleri (son 3'te olan) tekrar SEÇME
- Önceliği yüksek hedefe bağlı görevi tercih et
- Gerekirse tamamen yeni bir görev tanımla

SADECE JSON:
{{"aksiyon": "mevcut_gorev", "task_id": "T-001", "sebep": "..."}}
{{"aksiyon": "yeni_gorev", "goal_id": "G-001", "baslik": "...", "adimlar": [{{"sirano":1,"arac":"web_search","parametre":{{"task":"..."}},"durum":"bekliyor"}}], "sebep": "..."}}
{{"aksiyon": "bekle", "bekle_dakika": 60, "sebep": "..."}}"""

        cikti = _llm_cagir(prompt, max_tokens=1100, temperature=0.25)
        plan  = _parse_karar(cikti)
        if plan is None:
            plan = {"aksiyon": "bekle", "bekle_dakika": 60,
                    "sebep": "Planlama yanıtı parse edilemedi"}
        _log.info(f"[PLAN] Sonraki: {plan}")
        return plan

    # ── [7] UYKU ZAMANLA ──────────────────────────────
    def uyku_zamanla(self, dakika: int):
        """
        Bir sonraki uyanış zamanını memory/next_wakeup.json'a yaz.
        idle_loop.py bu dosyayı kontrol eder (FAZ 5 entegrasyonu).
        """
        ts = (datetime.datetime.now() +
              datetime.timedelta(minutes=dakika)).isoformat(timespec="seconds")
        NEXT_WAKEUP.write_text(
            json.dumps({"ts": ts, "dakika": dakika}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        _log.info(f"[UYKU] Sonraki uyanış: {ts} ({dakika} dakika sonra)")
        _telegram(f"💤 Kuroshin uyuyor — {dakika} dakika sonra uyanacak\n({ts})")

    # ── TAM DÖNGÜ ─────────────────────────────────────
    def calistir(self):
        """
        Tam OODA döngüsü:
        uyan → karar_ver → gorev_calistir → degerlendir → guncelle → planla_sonraki → uyku_zamanla
        """
        _log.info("=" * 60)
        _log.info("[OTURUM] Ajan döngüsü başlıyor")

        # [1] Uyan
        self.uyan()

        while self.oturum_gorev_sayisi < MAX_GOREV_PER_OTURUM:
            # [2] Karar ver
            karar = self.karar_ver()
            if karar is None:
                _log.error("[OTURUM] Karar alınamadı, çıkılıyor.")
                break

            k = karar.get("karar", "C")

            # C: Bekle
            if k == "C":
                dakika = int(karar.get("bekle_dakika", 120))
                _log.info(f"[OTURUM] Bekle kararı: {karar.get('sebep','')} ({dakika}dk)")
                self.uyku_zamanla(dakika)
                break

            # A: Mevcut görev
            if k == "A":
                task_id = karar.get("task_id", "")
                task    = next((t for t in self.tasks if t["id"] == task_id), None)
                if task is None:
                    # Tasks listesini tüm durumlarla yeniden dene
                    tum = load_tasks()
                    task = next((t for t in tum if t["id"] == task_id), None)
                if task is None:
                    _log.warning(f"[OTURUM] Görev bulunamadı: {task_id}")
                    break

            # B: Yeni görev oluştur
            elif k == "B":
                goal_id = karar.get("goal_id", "")
                baslik  = karar.get("baslik", "Model tarafından oluşturulan görev")
                adimlar = karar.get("adimlar", [
                    {"sirano": 1, "arac": "web_search",
                     "parametre": {"task": baslik}, "durum": "bekliyor"}
                ])
                yeni_id = add_task(goal_id=goal_id, baslik=baslik, adimlar=adimlar)
                _log.info(f"[OTURUM] Yeni görev oluşturuldu: {yeni_id}")
                tum = load_tasks()
                task = next((t for t in tum if t["id"] == yeni_id), None)
                if task is None:
                    _log.warning(f"[OTURUM] Yeni görev {yeni_id} listede bulunamadı")
                    break
            else:
                _log.warning(f"[OTURUM] Bilinmeyen karar: {k}")
                break

            # [3] Görev çalıştır
            try:
                sonuc = self.gorev_calistir(task)
            except Exception as e:
                _log.error(f"[OTURUM] Görev hatası: {e}\n{traceback.format_exc()}")
                update_task(task["id"], durum="bloke", hata=str(e)[:300])
                send_task_blocked(_chat_id(), task, f"İstisna: {str(e)[:120]}")
                break

            # Adım limiti veya kullanıcı durdurma — context zaten kaydedildi,
            # değerlendirme ve tamamlama YAPMA; bağlamı koru, döngüyü bitir.
            _yarida_kaldi = ("[ADIM LİMİTİ]" in sonuc or
                             "[KULLANICI DURDURDU]" in sonuc or
                             "[ONAY BEKLENİYOR" in sonuc)
            if _yarida_kaldi:
                _log.info(f"[OTURUM] Görev yarıda kaldı — context korunuyor, degerlendir atlanıyor.")
                if "[ONAY BEKLENİYOR" in sonuc:
                    self.uyku_zamanla(30)
                    _log.info("[OTURUM] HITL bloke — 30dk sonra wakeup ayarlandı (next_wakeup.json)")
                break

            # [4] Değerlendir
            reflection = self.degerlendir(task, sonuc)

            # [5] Güncelle
            self.guncelle(task, sonuc, reflection)

            send_task_complete(_chat_id(), task, reflection)

            self.oturum_gorev_sayisi += 1

            # [6] Planla sonraki
            plan = self.planla_sonraki(task, reflection)
            aksiyon = plan.get("aksiyon", "bekle")

            if aksiyon == "bekle":
                self.uyku_zamanla(int(plan.get("bekle_dakika", 120)))
                break
            elif aksiyon == "mevcut_gorev":
                # Listelerini güncelle, döngü devam etsin
                self.tasks = load_tasks(durum="bekliyor") + load_tasks(durum="aktif")
                self.ctx   = load_context()
                continue
            elif aksiyon == "yeni_gorev":
                yeni_id = add_task(
                    goal_id = plan.get("goal_id", ""),
                    baslik  = plan.get("baslik", "Planlanan görev"),
                    adimlar = plan.get("adimlar", [
                        {"sirano": 1, "arac": "web_search",
                         "parametre": {"task": plan.get("baslik", "")},
                         "durum": "bekliyor"}
                    ])
                )
                _log.info(f"[PLAN] Yeni görev eklendi: {yeni_id}")
                self.tasks = load_tasks(durum="bekliyor") + load_tasks(durum="aktif")
                continue
            else:
                break

        _log.info(f"[OTURUM] Döngü bitti. Çalıştırılan görev: {self.oturum_gorev_sayisi}")


if __name__ == "__main__":
    ajan = KuroshinAjan()
    ajan.calistir()
