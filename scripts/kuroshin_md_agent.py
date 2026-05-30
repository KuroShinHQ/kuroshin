"""
Kuroshin MD Öz-Güncelleme Modülü — FAZ 6
F6-02: _md_guncelle()   — ana güncelleme fonksiyonu
F6-03: _md_yedek_al()   — yedek alma
F6-04: _todo_tamamla()  — - [ ] X → - [x] X (ajan, tarih)
F6-05: _bolume_ekle()   — başlık altına madde ekleme
F6-07: _pending_md_guncelleme() — ARCHITECTURE.md Telegram onay mekanizması

MD Kuralları (OTONOM_AJAN_PROTOKOLU.md §6.2):
  MD-01: Yalnızca izin verilen dosyalar
  MD-02: Format bozulmadan içerik ekle/değiştir
  MD-03: (ajan, YYYY-MM-DD) iz etiketi
  MD-04: ARCHITECTURE.md → kullanıcı onayı
  MD-05: Güncelleme öncesi yedek al
  MD-06: Tek çağrıda tek bölüm
"""
import re
import json
import shutil
import logging
import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

BASE_DIR   = Path("/mnt/c/Kuroshin")
BACKUP_DIR = BASE_DIR / "memory" / "md_backups"
PENDING_MD = Path("/tmp/kuroshin_pending_md.json")

load_dotenv(BASE_DIR / ".env")
_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

_log = logging.getLogger("md_agent")

# MD-01: İzin verilen dosyalar + güncelleme yetkisi
_IZIN_LISTESI = {
    "OTONOM_AJAN_PROTOKOLU.md": ["*"],          # tüm bölümler
    "KUROSHIN_MASTER_ROADMAP.md": ["*"],
    "YAPILACAK_GOREVLER.md": ["*"],
}
_ONAY_GEREKEN = {
    "ARCHITECTURE.md": [
        "Anlık Servis Durumu",
        "Araştırma Bulguları",
    ]
}


def _izin_kontrol(dosya_yolu: str, bolum: str) -> tuple[bool, str]:
    """
    Dosya + bölüm kombinasyonunun güncelleme iznini kontrol et.
    (True, "onay") → önce Telegram onayı gerekli
    (True, "direkt") → direkt yaz
    (False, sebep) → yasak
    """
    ad = Path(dosya_yolu).name
    if ad in _IZIN_LISTESI:
        izinler = _IZIN_LISTESI[ad]
        if "*" in izinler or bolum in izinler:
            return True, "direkt"
    if ad in _ONAY_GEREKEN:
        bolum_izin = _ONAY_GEREKEN[ad]
        if "*" in bolum_izin or any(b in bolum for b in bolum_izin):
            return True, "onay"
        return False, f"MD-01: '{bolum}' bölümü için yetki yok ({ad})"
    return False, f"MD-01: '{ad}' dosyası güncellenemez"


# ── F6-03: YEDEK AL ───────────────────────────────────

def _md_yedek_al(dosya_yolu: str) -> Path | None:
    """MD-05: Güncelleme öncesi memory/md_backups/DOSYA_TARIH.md yedeği al."""
    try:
        kaynak = Path(dosya_yolu)
        if not kaynak.exists():
            return None
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ad  = kaynak.stem
        ext = kaynak.suffix
        hedef = BACKUP_DIR / f"{ad}_{ts}{ext}"
        shutil.copy(kaynak, hedef)  # copy2 kaynak mtime'ını korur → yeni zaman damgası için copy kullan
        _log.info(f"[MD-05] Yedek: {hedef.name}")
        return hedef
    except Exception as e:
        _log.error(f"[MD-05] Yedek alma hatası: {e}")
        return None


# ── F6-04: TODO TAMAMLA ───────────────────────────────

def _todo_tamamla(icerik: str, gorev_baslik: str) -> str:
    """
    MD-03: `- [ ] GOREV_BASLIK` satırını `- [x] GOREV_BASLIK (ajan, YYYY-MM-DD)` yap.
    gorev_baslik'in başındaki **F1-01** gibi bold prefix'e göre eşleşir.
    """
    tarih = datetime.date.today().isoformat()
    etiket = f" (ajan, {tarih})"

    # Önce tam eşleşme dene
    pattern = re.compile(
        r"(- \[ \] )(" + re.escape(gorev_baslik) + r")(.*?)$",
        re.MULTILINE
    )
    if pattern.search(icerik):
        return pattern.sub(rf"- [x] \2\3{etiket}", icerik)

    # Bold prefix varsa (**F1-01** gibi) kısmi eşleşme
    kisa = gorev_baslik.split("·", 1)[-1].strip()[:40]
    pattern2 = re.compile(
        r"(- \[ \] )(\*\*\w+-\d+\*\* · [^\n]*?" + re.escape(kisa) + r"[^\n]*?)$",
        re.MULTILINE
    )
    if pattern2.search(icerik):
        return pattern2.sub(rf"- [x] \2{etiket}", icerik)

    _log.warning(f"[MD-04] todo_tamamla: '{gorev_baslik[:50]}' bulunamadı")
    return icerik


# ── F6-05: BÖLÜME EKLE ────────────────────────────────

def _bolume_ekle(icerik: str, bolum: str, yeni_satir: str) -> str:
    """
    MD-06: Belirtilen ## başlık altına yeni madde ekle.
    Bir sonraki ## başlıktan önce yerleştirir.
    yeni_satir içinde (ajan, tarih) etiketi olmalı — MD-03.
    """
    tarih = datetime.date.today().isoformat()
    # MD-03: etiket yoksa ekle
    if "(ajan," not in yeni_satir:
        yeni_satir = yeni_satir.rstrip() + f" (ajan, {tarih})"

    satirlar = icerik.split("\n")
    hedef_idx = None
    for idx, satir in enumerate(satirlar):
        # ## ile başlayan başlık, büyük/küçük harf duyarsız içerik karşılaştırması
        if satir.startswith("##") and bolum.strip() in satir:
            hedef_idx = idx
            break

    if hedef_idx is None:
        _log.warning(f"[MD-05] Bölüm bulunamadı: '{bolum}'")
        return icerik  # değiştirme

    # Bir sonraki ## başlığı veya dosya sonunu bul
    ekleme_idx = len(satirlar)
    for idx in range(hedef_idx + 1, len(satirlar)):
        if satirlar[idx].startswith("##"):
            ekleme_idx = idx
            break

    # Boş satırı koru — son içerik satırından önce ekle
    # Boş satır varsa ondan önce, yoksa doğrudan ekle
    while ekleme_idx > hedef_idx + 1 and not satirlar[ekleme_idx - 1].strip():
        ekleme_idx -= 1

    satirlar.insert(ekleme_idx, yeni_satir)
    return "\n".join(satirlar)


# ── F6-07: PENDING — ARCHITECTURE.MD ONAY ────────────

def _pending_md_guncelleme(dosya_yolu: str, bolum: str,
                            yeni_icerik: str, tur: str = "bulgu_ekle"):
    """
    MD-04: ARCHITECTURE.md güncellemesini Telegram onayına gönder.
    Onay gelince chancellor callback'i /tmp/kuroshin_pending_md.json okur.
    """
    try:
        payload = {
            "dosya": dosya_yolu,
            "bolum": bolum,
            "icerik": yeni_icerik,
            "tur": tur,
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        PENDING_MD.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        _log.info(f"[MD-04] Onay bekleniyor: {Path(dosya_yolu).name} / {bolum}")

        # Telegram bildirimi
        if _TOKEN and _CHAT_ID:
            mesaj = (
                f"📝 <b>MD Güncelleme Onayı Gerekli</b>\n"
                f"Dosya : <code>{Path(dosya_yolu).name}</code>\n"
                f"Bölüm : {bolum[:60]}\n"
                f"Tür   : {tur}\n"
                f"İçerik: <pre>{yeni_icerik[:200]}</pre>\n\n"
                f"Telegram'dan ✅ veya ❌ ile yanıtla."
            )
            keyboard = [[
                {"text": "✅ Onayla", "callback_data": "md_onayla"},
                {"text": "❌ İptal",  "callback_data": "md_iptal"},
            ]]
            requests.post(
                f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
                json={
                    "chat_id": _CHAT_ID,
                    "text": mesaj,
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": keyboard},
                },
                timeout=10,
            )
    except Exception as e:
        _log.error(f"[MD-04] Pending yazma hatası: {e}")


# ── F6-02: ANA GÜNCELLEME FONKSİYONU ────────────────

def md_guncelle(dosya_yolu: str, bolum: str,
                yeni_icerik: str, tur: str) -> dict:
    """
    Ana MD güncelleme fonksiyonu — protokoldeki 6.4 şablonu.

    tur: "bulgu_ekle" | "todo_guncelle" | "not_ekle" | "versiyon_guncelle"

    Döner: {"ok": bool, "durum": str, "yedek": str|None}
    """
    _log.info(f"[MD] Güncelleme isteği: {Path(dosya_yolu).name} / {bolum} ({tur})")

    # İzin kontrolü
    izin, mod = _izin_kontrol(dosya_yolu, bolum)
    if not izin:
        _log.warning(f"[MD-01] Yetki yok: {mod}")
        return {"ok": False, "durum": f"yetki_yok: {mod}", "yedek": None}

    # Onay gerekiyorsa
    if mod == "onay":
        _pending_md_guncelleme(dosya_yolu, bolum, yeni_icerik, tur)
        return {"ok": False, "durum": "onay_bekleniyor", "yedek": None}

    # Dosya var mı?
    p = Path(dosya_yolu)
    if not p.exists():
        _log.warning(f"[MD] Dosya bulunamadı: {dosya_yolu}")
        return {"ok": False, "durum": "dosya_yok", "yedek": None}

    # MD-05: Yedek
    yedek = _md_yedek_al(dosya_yolu)

    # Oku
    icerik = p.read_text(encoding="utf-8")

    # Uygula
    try:
        if tur == "todo_guncelle":
            yeni = _todo_tamamla(icerik, yeni_icerik)
        elif tur in ("bulgu_ekle", "not_ekle", "versiyon_guncelle"):
            yeni = _bolume_ekle(icerik, bolum, yeni_icerik)
        else:
            return {"ok": False, "durum": f"bilinmeyen_tur: {tur}", "yedek": str(yedek)}

        if yeni == icerik:
            _log.warning(f"[MD] Değişiklik yapılmadı (eşleşme yok?): {bolum}")
            return {"ok": False, "durum": "degisiklik_yok", "yedek": str(yedek)}

        # MD-02: Yaz
        p.write_text(yeni, encoding="utf-8")
        _log.info(f"[MD] ✅ Güncellendi: {p.name} / {bolum} ({tur})")
        return {"ok": True, "durum": "guncellendi", "yedek": str(yedek)}

    except Exception as e:
        _log.error(f"[MD] Güncelleme hatası: {e}")
        return {"ok": False, "durum": f"hata: {e}", "yedek": str(yedek)}
