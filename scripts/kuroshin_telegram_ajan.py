"""
Kuroshin Otonom Ajan — Telegram Bildirim Katmanı (FAZ 3)
Tüm ajan ilerleme, bloke, tamamlanma ve günlük özet mesajları buradan gider.
"""
import os
import json
import datetime
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path("/mnt/c/Kuroshin/.env"))

_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
_BASE    = f"https://api.telegram.org/bot{_TOKEN}"
_log     = logging.getLogger("tg_ajan")

MEMORY_DIR = Path("/mnt/c/Kuroshin/memory")


# ── TEMEL GÖNDERİCİ ───────────────────────────────────

def _gonder(chat_id: str | int, metin: str,
            keyboard: list | None = None) -> int | None:
    """
    Telegram'a HTML mesaj gönder. Başarıda message_id döner.
    Token/chat_id yoksa sessizce None döner.
    """
    if not _TOKEN or not _CHAT_ID:
        _log.warning("[TG] Token/chat_id eksik — mesaj gönderilmedi.")
        return None
    payload: dict = {
        "chat_id": chat_id or _CHAT_ID,
        "text": metin,
        "parse_mode": "HTML",
    }
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    try:
        r = requests.post(f"{_BASE}/sendMessage", json=payload, timeout=10)
        result = r.json()
        if result.get("ok"):
            return result.get("result", {}).get("message_id")
        _log.warning(f"[TG] Hata: {result.get('description','')}")
    except Exception as e:
        _log.warning(f"[TG] İstek hatası: {e}")
    return None


def _duzenle(chat_id: str | int, message_id: int, metin: str):
    """Mevcut mesajı düzenle (canlı güncelleme)."""
    if not _TOKEN:
        return
    try:
        requests.post(f"{_BASE}/editMessageText", json={
            "chat_id": chat_id or _CHAT_ID,
            "message_id": message_id,
            "text": metin,
            "parse_mode": "HTML",
        }, timeout=10)
    except Exception as e:
        _log.warning(f"[TG] Düzenleme hatası: {e}")


# ── F3-02: GÖREV BAŞLANGIÇ ────────────────────────────

def send_task_start(chat_id, task: dict) -> int | None:
    """Görev başlangıç mesajı gönder. message_id döner (sonraki adımlar günceller)."""
    adim_say = len(task.get("adimlar", []))
    metin = (
        f"🤖 <b>GÖREV BAŞLADI</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Görev   : {task.get('baslik', '')}\n"
        f"Hedef   : {task.get('goal_id', '')}\n"
        f"Adımlar : {adim_say}\n"
        f"ID      : {task.get('id', '')}"
    )
    return _gonder(chat_id, metin)


# ── F3-01: ADIM İLERLEME ─────────────────────────────

def send_task_progress(chat_id, task: dict, adim_no: int,
                       toplam_adim: int, arac_adi: str,
                       durum: str = "calisiyor",
                       sure_s: float | None = None) -> int | None:
    """
    Tek adım bildirimi.
    durum: 'calisiyor' | 'tamamlandi' | 'hata'
    """
    emoji = {"calisiyor": "🔧", "tamamlandi": "✅", "hata": "❌"}.get(durum, "•")
    sure_str = f" ({sure_s:.1f}s)" if sure_s is not None else ""
    metin = (
        f"{emoji} Adım {adim_no}/{toplam_adim} — <b>{arac_adi}</b>{sure_str}\n"
        f"   Görev: {task.get('baslik', '')[:60]}"
    )
    return _gonder(chat_id, metin)


# ── F3-03: GÖREV TAMAMLAMA ────────────────────────────

def send_task_complete(chat_id, task: dict, reflection: dict,
                       sure_toplam_s: float | None = None) -> int | None:
    """Görev tamamlandı bildirimi — reflection özeti dahil."""
    sure_str = f"\nSüre   : {sure_toplam_s:.1f}s" if sure_toplam_s else ""
    kalite   = reflection.get("kalite_skoru", "?")
    ders     = reflection.get("ders", "")[:100]
    oneri    = reflection.get("sonraki_oneri", "")[:80]

    # Bir sonraki bekleyen görevi bul
    try:
        from scripts.kuroshin_goals import load_tasks
        sonraki = load_tasks(durum="bekliyor", limit=1)
        sonraki_str = f"\nSıradaki: {sonraki[0]['id']} — {sonraki[0]['baslik'][:50]}" \
                      if sonraki else ""
    except Exception:
        sonraki_str = ""

    metin = (
        f"✅ <b>GÖREV TAMAMLANDI</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Görev  : {task.get('baslik', '')}{sure_str}\n"
        f"Kalite : {kalite}\n"
        f"Ders   : {ders}\n"
        f"Öneri  : {oneri}"
        f"{sonraki_str}"
    )
    return _gonder(chat_id, metin)


# ── F3-04: BLOKE GÖREV ────────────────────────────────

_PENDING_FILE = Path("/tmp/kuroshin_pending_tasks.json")

def gorev_pending_kaydet(task: dict):
    """
    F5-04: Onay bekleyen görevi dosyaya yaz.
    Chancellor başlatma sırasında bu dosyayı okuyarak _PENDING_TASKS'a yükler.
    """
    try:
        mevcut: dict = {}
        if _PENDING_FILE.exists():
            mevcut = json.loads(_PENDING_FILE.read_text(encoding="utf-8"))
        mevcut[task["id"]] = task
        _PENDING_FILE.write_text(json.dumps(mevcut, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        _log.warning(f"[PENDING] Kayıt hatası: {e}")


def send_task_blocked(chat_id, task: dict, sebep: str,
                      onay_gerektiren: bool = False) -> int | None:
    """
    Bloke bildirimi. onay_gerektiren=True ise inline ✅/❌ keyboard ekler.
    Görev F5-04 pending dosyasına da yazılır.
    """
    if onay_gerektiren:
        gorev_pending_kaydet(task)

    metin = (
        f"⚠️ <b>GÖREV BLOKE</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Görev : {task.get('baslik', '')}\n"
        f"ID    : {task.get('id', '')}\n"
        f"Sebep : {sebep}"
    )
    keyboard = None
    if onay_gerektiren:
        metin += "\nAksiyon: ✅ Onayla veya ❌ İptal"
        keyboard = [[
            {"text": "✅ Onayla",
             "callback_data": f"gorev_onayla_{task.get('id','')}"},
            {"text": "❌ İptal",
             "callback_data": f"gorev_iptal_{task.get('id','')}"},
        ]]
    return _gonder(chat_id, metin, keyboard=keyboard)


# ── F3-05: GÜNLÜK OTONOM ÖZET ────────────────────────

def send_daily_summary(chat_id) -> int | None:
    """
    22:00 günlük otonom özet.
    Tamamlanan/bloke/aktif görevleri + hedef ilerlemelerini raporlar.
    Chancellor'ın _aktivite_gunluk_ozet() ile entegre çalışır.
    """
    try:
        from scripts.kuroshin_goals import load_tasks, load_goals
    except ImportError:
        import sys
        sys.path.insert(0, "/mnt/c/Kuroshin")
        from scripts.kuroshin_goals import load_tasks, load_goals

    bugun = datetime.date.today().isoformat()

    tamamlanan = load_tasks(durum="tamamlandi")
    bloke      = load_tasks(durum="bloke")
    bekleyen   = load_tasks(durum="bekliyor")
    goals      = load_goals(durum="aktif")

    # Bugün tamamlananları filtrele
    bugun_tam = [
        t for t in tamamlanan
        if t.get("bitis_ts", "").startswith(bugun)
    ]
    bugun_blk = [
        t for t in bloke
        if t.get("bitis_ts", "").startswith(bugun)
    ]

    hedef_satirlar = ""
    for g in goals[:5]:
        hedef_satirlar += f"  • [{g['id']}] {g['baslik'][:45]} — %{g['ilerleme']}\n"
    if not hedef_satirlar:
        hedef_satirlar = "  (Aktif hedef yok)\n"

    # Yarın sıradaki
    yarinki = bekleyen[:2]
    yarin_str = ""
    for t in yarinki:
        yarin_str += f"  → {t['id']} — {t['baslik'][:50]}\n"
    if not yarin_str:
        yarin_str = "  (Bekleyen görev yok)\n"

    metin = (
        f"📊 <b>GÜNLÜK OTONOM ÖZET ({bugun})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Tamamlanan : {len(bugun_tam)} görev\n"
        f"Bloke      : {len(bugun_blk)} görev\n"
        f"Bekleyen   : {len(bekleyen)} görev\n\n"
        f"<b>Aktif Hedefler:</b>\n{hedef_satirlar}\n"
        f"<b>Yarın Sırada:</b>\n{yarin_str}"
    )
    return _gonder(chat_id, metin)


# ── YARDIMCI: DURDURMA SİNYALİ ───────────────────────

_STOP_FILE = Path("/tmp/kuroshin_ajan_dur.flag")

def ajan_durdur():
    """Çalışan otonom döngüyü durdurma sinyali yaz."""
    _STOP_FILE.write_text("dur", encoding="utf-8")

def ajan_dur_mu() -> bool:
    """Döngü her adımda bunu kontrol eder."""
    if _STOP_FILE.exists():
        _STOP_FILE.unlink(missing_ok=True)
        return True
    return False
