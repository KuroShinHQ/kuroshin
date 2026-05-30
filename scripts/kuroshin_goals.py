"""
Kuroshin Hedef & Görev Yönetimi — FAZ 1 Altyapısı
goals.json / tasks.json / task_context.json CRUD katmanı.
"""
import json
import datetime
from pathlib import Path

MEMORY_DIR   = Path("/mnt/c/Kuroshin/memory")
GOALS_FILE   = MEMORY_DIR / "goals.json"
GECMIS_FILE  = MEMORY_DIR / "gorev_gecmisi.json"  # F4-04 döngü kırıcı
TASKS_FILE   = MEMORY_DIR / "tasks.json"
CONTEXT_FILE = MEMORY_DIR / "task_context.json"


def _oku(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _yaz(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _simdi() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ── GOALS ─────────────────────────────────────────────

def load_goals(durum: str = None) -> list:
    """Aktif (veya tüm) hedefleri döndür."""
    data = _oku(GOALS_FILE)
    goals = data.get("goals", [])
    if durum:
        goals = [g for g in goals if g.get("durum") == durum]
    return goals


def add_goal(baslik: str, aciklama: str = "", oncelik: int = 3,
             alt_hedefler: list = None) -> str:
    """Yeni hedef ekle. Oluşturulan ID'yi döndür."""
    data = _oku(GOALS_FILE)
    goals = data.get("goals", [])
    yeni_id = f"G-{len(goals) + 1:03d}"
    goals.append({
        "id": yeni_id,
        "baslik": baslik,
        "aciklama": aciklama,
        "oncelik": oncelik,
        "durum": "aktif",
        "ilerleme": 0,
        "alt_hedefler": alt_hedefler or [],
        "olusturma_ts": _simdi(),
        "son_guncelleme": _simdi(),
        "notlar": ""
    })
    _yaz(GOALS_FILE, {"goals": goals})
    return yeni_id


def update_goal(goal_id: str, durum: str = None, ilerleme: int = None,
                notlar: str = None) -> bool:
    data = _oku(GOALS_FILE)
    goals = data.get("goals", [])
    for g in goals:
        if g["id"] == goal_id:
            if durum is not None:
                g["durum"] = durum
            if ilerleme is not None:
                g["ilerleme"] = max(0, min(100, ilerleme))
            if notlar is not None:
                g["notlar"] = notlar
            g["son_guncelleme"] = _simdi()
            _yaz(GOALS_FILE, {"goals": goals})
            return True
    return False


# ── TASKS ─────────────────────────────────────────────

def load_tasks(durum: str = None, goal_id: str = None, limit: int = None) -> list:
    """Görevleri filtreli döndür. durum: bekliyor|aktif|tamamlandi|bloke|iptal"""
    data = _oku(TASKS_FILE)
    tasks = data.get("tasks", [])
    if durum:
        tasks = [t for t in tasks if t.get("durum") == durum]
    if goal_id:
        tasks = [t for t in tasks if t.get("goal_id") == goal_id]
    # Öncelik sırası
    tasks.sort(key=lambda t: t.get("oncelik", 99))
    if limit:
        tasks = tasks[:limit]
    return tasks


def add_task(goal_id: str, baslik: str, adimlar: list,
             oncelik: int = 2) -> str:
    """Yeni görev ekle. Oluşturulan ID'yi döndür."""
    data = _oku(TASKS_FILE)
    tasks = data.get("tasks", [])
    yeni_id = f"T-{len(tasks) + 1:03d}"
    tasks.append({
        "id": yeni_id,
        "goal_id": goal_id,
        "baslik": baslik,
        "durum": "bekliyor",
        "oncelik": oncelik,
        "adimlar": adimlar,
        "baslangic_ts": None,
        "bitis_ts": None,
        "sonuc": "",
        "hata": ""
    })
    _yaz(TASKS_FILE, {"tasks": tasks})
    return yeni_id


def update_task(task_id: str, durum: str = None, sonuc: str = None,
                hata: str = None, adim_index: int = None,
                adim_durum: str = None) -> bool:
    """Görev veya tek adım durumunu güncelle."""
    data = _oku(TASKS_FILE)
    tasks = data.get("tasks", [])
    for t in tasks:
        if t["id"] == task_id:
            if durum is not None:
                t["durum"] = durum
                if durum == "aktif" and not t.get("baslangic_ts"):
                    t["baslangic_ts"] = _simdi()
                if durum in ("tamamlandi", "iptal", "bloke"):
                    t["bitis_ts"] = _simdi()
            if sonuc is not None:
                t["sonuc"] = sonuc
            if hata is not None:
                t["hata"] = hata
            if adim_index is not None and adim_durum is not None:
                adimlar = t.get("adimlar", [])
                if 0 <= adim_index < len(adimlar):
                    adimlar[adim_index]["durum"] = adim_durum
            _yaz(TASKS_FILE, {"tasks": tasks})
            return True
    return False


# ── CONTEXT ───────────────────────────────────────────

def save_context(gorev_id: str, adim: int, ara_sonuclar: dict,
                 devam_notu: str = "") -> None:
    """Yarım kalan görev bağlamını kaydet."""
    _yaz(CONTEXT_FILE, {
        "aktif_gorev_id": gorev_id,
        "tamamlanan_adim": adim,
        "ara_sonuclar": ara_sonuclar,
        "devam_notu": devam_notu,
        "kayit_ts": _simdi()
    })


def load_context() -> dict:
    """Kalan bağlamı yükle. Boşsa {} döner."""
    return _oku(CONTEXT_FILE)


def clear_context() -> None:
    """Görev bitti, bağlamı sıfırla."""
    _yaz(CONTEXT_FILE, {
        "aktif_gorev_id": None,
        "tamamlanan_adim": 0,
        "ara_sonuclar": {},
        "devam_notu": "",
        "kayit_ts": _simdi()
    })


# ── ÖZET ──────────────────────────────────────────────

def hedef_ozeti() -> str:
    """Telegram için kısa hedef + görev özeti."""
    goals = load_goals(durum="aktif")
    bekleyen = load_tasks(durum="bekliyor")
    aktif    = load_tasks(durum="aktif")
    bloke    = load_tasks(durum="bloke")

    satirlar = [f"📌 <b>Aktif Hedefler ({len(goals)})</b>"]
    for g in goals:
        satirlar.append(f"  • [{g['id']}] {g['baslik']} — %{g['ilerleme']}")

    satirlar.append(f"\n📋 <b>Görevler</b>")
    satirlar.append(f"  Bekliyor : {len(bekleyen)}")
    satirlar.append(f"  Aktif    : {len(aktif)}")
    satirlar.append(f"  Bloke    : {len(bloke)}")

    ctx = load_context()
    if ctx.get("aktif_gorev_id"):
        satirlar.append(f"\n🔄 Yarım bırakılan: {ctx['aktif_gorev_id']} (adım {ctx['tamamlanan_adim']})")

    return "\n".join(satirlar)


# ── F4-03: HEDEF İLERLEME HESABI ─────────────────────

def hedef_ilerleme_guncelle(goal_id: str) -> int:
    """
    goal_id için tamamlanan / toplam görev oranından ilerleme yüzdesini hesapla,
    goals.json'a yaz ve yeni yüzdeyi döndür.
    """
    tum        = load_tasks(goal_id=goal_id)
    tamamlanan = [t for t in tum if t.get("durum") == "tamamlandi"]
    if not tum:
        return 0
    yuzde = int(len(tamamlanan) / len(tum) * 100)
    update_goal(goal_id, ilerleme=yuzde)
    return yuzde


# ── F4-04: DÖNGÜ KIRICI — Görev Geçmişi ──────────────

_GECMIS_LIMIT = 5   # son kaç görevi hatırla

def gorev_gecmisi_yukle() -> list:
    """Son tamamlanan görev ID listesini döndür."""
    try:
        return _oku(GECMIS_FILE).get("gecmis", [])
    except Exception:
        return []


def gorev_gecmisi_guncelle(task_id: str) -> None:
    """Tamamlanan görevi geçmişe ekle, limitin üstündekini at."""
    gecmis = gorev_gecmisi_yukle()
    if task_id in gecmis:
        gecmis.remove(task_id)
    gecmis.append(task_id)
    if len(gecmis) > _GECMIS_LIMIT:
        gecmis = gecmis[-_GECMIS_LIMIT:]
    _yaz(GECMIS_FILE, {"gecmis": gecmis, "son_guncelleme": _simdi()})


def dongu_kirici_kontrol(task_id: str, son_n: int = 3) -> bool:
    """
    True döner → bu görev son N görev içinde tekrarlıyor, seçme.
    """
    gecmis = gorev_gecmisi_yukle()
    return task_id in gecmis[-son_n:]


# ── F6-01: ARAŞTIRMA KALİTE KONTROLÜ ─────────────────

_KAY03_MIN_KARAKTER = 80    # KAY-03: minimum sonuç uzunluğu
_KAY07_MAX_DENEME   = 3     # KAY-07: aynı sorgu max deneme

# Deneme sayacı — sorgular arası paylaşımlı (bellekte), max 200 giriş
_sorgu_deneme: dict = {}
_SD_MAXSIZE = 200


def _arastirma_kalite_kontrol(sonuc: str, sorgu: str = "") -> dict:
    """
    F6-01: Araştırma sonucunu KAY-03 ve KAY-07 kurallarına göre denetle.

    Döner:
      {"gecti": True,  "sebep": ""}                 → kullanılabilir
      {"gecti": False, "sebep": "kisa|limit_asti"}   → atla veya bloke et
    """
    # KAY-03: Minimum uzunluk
    if len(sonuc.strip()) < _KAY03_MIN_KARAKTER:
        return {"gecti": False, "sebep": "kisa",
                "detay": f"Sonuç {len(sonuc)} karakter < {_KAY03_MIN_KARAKTER} minimum"}

    # KAY-07: Aynı sorgu tekrar sayısı
    if sorgu:
        if len(_sorgu_deneme) >= _SD_MAXSIZE:
            _sorgu_deneme.clear()
        _sorgu_deneme[sorgu] = _sorgu_deneme.get(sorgu, 0) + 1
        if _sorgu_deneme[sorgu] > _KAY07_MAX_DENEME:
            return {"gecti": False, "sebep": "limit_asti",
                    "detay": f"'{sorgu[:40]}' {_KAY07_MAX_DENEME}+ kez denendi"}

    return {"gecti": True, "sebep": "", "detay": ""}


def sorgu_deneme_sifirla(sorgu: str = "") -> None:
    """Görev tamamlandıktan sonra deneme sayacını sıfırla."""
    if sorgu:
        _sorgu_deneme.pop(sorgu, None)
    else:
        _sorgu_deneme.clear()
