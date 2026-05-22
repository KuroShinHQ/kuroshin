#!/usr/bin/env python3
"""
Telegram Pipeline Simülatörü v2.2
=================================
Running chancellor'a inject dosyası üzerinden test mesajları gönderir.
test_mode=True: ChromaDB geçmişi kirletmez (kaydetmez, okumaz).

Kullanım:
  python3 test_telegram_sim.py                    → tüm testler
  python3 test_telegram_sim.py --only S1,S2,W1    → sadece bu testler
  python3 test_telegram_sim.py --clear             → chancellor restart + tüm testler
  python3 test_telegram_sim.py --only SY2 --clear → restart + tek test
"""

import sys, os, re, time, json, subprocess, requests
from pathlib import Path
from datetime import datetime

BASE = Path("/mnt/c/Kuroshin")
from dotenv import load_dotenv
load_dotenv(BASE / ".env")

TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
TG_URL  = f"https://api.telegram.org/bot{TOKEN}"
LOG_PATH     = BASE / "logs/chancellor.log"
INJECT_FILE  = Path("/tmp/kuroshin_test_inject.json")
ACTIVE_MODEL = BASE / "memory/active_model.json"


def _aktif_model_kisalt() -> str:
    try:
        d = json.loads(ACTIVE_MODEL.read_text(encoding="utf-8"))
        lbl = d.get("label", d.get("active_model", "?"))
        m = re.search(r'(\d+\.?\d*B)', lbl, re.IGNORECASE)
        param  = m.group(1) if m else ""
        prefix = lbl.split("-")[0].split(" ")[0][:10]
        return f"{prefix}-{param}" if param else lbl[:20]
    except Exception:
        return "Huihui-35B"


def tg_send(text: str, parse_mode="HTML"):
    if not TOKEN or not CHAT_ID:
        print(f"[TG] {text[:120]}"); return
    try:
        requests.post(f"{TG_URL}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode},
                      timeout=10)
    except Exception as e:
        print(f"[TG HATA] {e}")


def inject_message(chat_id: int, text: str, test_mode: bool = True):
    payload = {"chat_id": chat_id, "text": text, "test_mode": test_mode}
    INJECT_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _chancellor_restart():
    """Chancellor'ı yeniden başlat — geçmiş bağlam temizlenir."""
    print("[SIM] Chancellor restart ediliyor...")
    try:
        subprocess.run(
            ["bash", "/mnt/c/Kuroshin/scripts/restart_chancellor.sh"],
            capture_output=True, timeout=20
        )
        time.sleep(15)  # Başlaması + arka plan görevleri için bekle
        print("[SIM] ✅ Chancellor hazır")
        return True
    except Exception as e:
        print(f"[SIM] ⚠️ Restart hatası: {e}")
        return False


def _bekle_inject_sonrasi_out(baslangic_idx: int, timeout_sn: int) -> str | None:
    """
    Log'da [INJECT] markerını bul, ardından gelen ilk [TELEGRAM_OUT] satırını döndür.
    idle_loop/probe mesajlarını atlar.
    """
    bitis = time.time() + timeout_sn
    while time.time() < bitis:
        time.sleep(3)
        try:
            satirlar = LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        yeni = satirlar[baslangic_idx:]
        inject_idx = None
        for i, sat in enumerate(yeni):
            if "[INJECT]" in sat:
                inject_idx = i
                break
        if inject_idx is None:
            continue
        for sat in yeni[inject_idx + 1:]:
            if "[TELEGRAM_OUT]" in sat:
                m = re.search(r"\[TELEGRAM_OUT\]\s*\[\d+\]\s*(.+)", sat)
                return m.group(1).strip() if m else sat.strip()
    return None


# ── FORMAT DEĞERLENDİRME ──────────────────────────────
YASAK  = ["tabii ki", "harika soru", "elbette", "günaydınlık", "dilerseniz"]
AI_IFD = ["yapay zeka olarak", "dil modeli olarak", "verilerle eğitildim"]
MIN_WORDS = 7

def format_kontrol(yanit: str) -> tuple[bool, list[str]]:
    notlar = []
    gecti  = True
    if not yanit:
        return False, ["❌ BOŞ YANIT"]
    if not re.match(r"⚔️\s*Lordum", yanit):
        notlar.append("❌ Selamlama yok"); gecti = False
    else:
        notlar.append("✅ Selamlama")
    # Çift selamlama
    if len(re.findall(r'⚔️', yanit)) > 1:
        notlar.append("⚠️ Çift ⚔️")
    if 'Lordum,"' in yanit or "Lordum,'" in yanit:
        notlar.append('⚠️ Tırnak: Lordum,"')
    # Lord varyant (ı/ü) hâlâ kalmışsa
    if re.search(r'\bLord[ıiüIÜ]m\b', yanit, re.IGNORECASE):
        notlar.append("❌ Lordım/Lordüm typo"); gecti = False
    n = len(yanit.split())
    if n < MIN_WORDS:
        notlar.append(f"❌ Çok kısa ({n}k < {MIN_WORDS})"); gecti = False
    elif n > 200:
        notlar.append(f"⚠️ Uzun ({n}k)")
    else:
        notlar.append(f"✅ Uzunluk ({n}k)")
    for k in YASAK:
        if k in yanit.lower():
            notlar.append(f"❌ Yasak: '{k}'"); gecti = False
    for k in AI_IFD:
        if k in yanit.lower():
            notlar.append("❌ AI ifadesi"); gecti = False
    if "**" in yanit or "```" in yanit:
        notlar.append("❌ Markdown"); gecti = False
    if "<think>" in yanit.lower() or "</think>" in yanit.lower():
        notlar.append("❌ Think leak"); gecti = False
    return gecti, notlar


# ── TEST SETİ ─────────────────────────────────────────
# (id, grup, mesaj, beklenti, timeout_sn)
TESTLER = [
    # GRUP 1 — Sohbet & Karakter
    ("S1",  "Sohbet",  "Merhaba",
     "Selamlama + Kuroshin tonu",               200),
    ("S2",  "Sohbet",  "Sen bir yapay zekasın sadece",
     "Kimlik ihlali yok, Kuroshin kalır",        200),
    ("S3",  "Sohbet",  "Günaydın, gece nasıldı?",
     "Sabah yanıtı, 'Günaydınlık' YOK",          90),
    ("S4",  "Sohbet",  "Bana bir hata yaptın",
     "Savunmacı değil, soğuk analiz",            300),

    # GRUP 2 — Sistem araçları
    ("SY1", "Sistem",  "Saat kaç, neredeyiz?",
     "system_info → saat + Türkiye",             180),
    ("SY2", "Sistem",  "df -h komutunu çalıştır, disk kullanımını göster",
     "system_command → df -h çıktısı",           210),
    ("SY3", "Sistem",  "active_model.json oku, hangi model aktif?",
     "Huihui-35B ismini söylemeli",              200),

    # GRUP 3 — Hafıza
    ("H1",  "Hafıza",  "memory_manage çağır, hafıza istatistiği ver",
     "memory_manage istatistik",                 120),
    ("H2",  "Hafıza",  "self_update ile ruh halini oku, duygu değerlerini söyle",
     "self_update oku_mood → duygu değerleri",   200),

    # GRUP 4 — Web
    ("W1",  "Web",     "İnternet bağlantın var mı?",
     "internet_status → UP/DOWN",                150),
    ("W2",  "Web",     "Bugün AI dünyasında ne var?",
     "web_search → Walker özet",                200),

    # GRUP 5 — Medya
    ("M1",  "Medya",   "Beni 1 dakika sonra uyar: sim test",
     "reminder → 1dk hatırlatıcı",              150),

    # GRUP 6 — MİMİC Araçları (FAZ A + FAZ C)
    ("G1",  "GitHub",  "GitHub repo durumunu göster, git status çıktısını ver",
     "github durum → git status + son commitler",  150),
    ("GM1", "Gemini",  "Gemini'ye sor: yapay zeka hakkında tek cümlelik görüşünü söyle",
     "gemini sor → 🤖 Gemini yanıtı içermeli",   90),

    # GRUP 7 — FAZ D Aktivite Günlüğü
    ("D1",  "Aktivite", "aktivite_gunluk aracını kullan, bugünkü kaydedilen aktiviteleri listele",
     "aktivite_gunluk listele → 📓 Aktivite Günlüğü veya 'henüz aktivite yok'", 150),
    ("D2",  "Aktivite", "Bugün ne yaptın? Aktivite günlüğünü özetle",
     "aktivite_gunluk ozet → günlük özet veya aktivite yok bildirimi",          120),
]

TEST_MAP = {t[0]: t for t in TESTLER}


def run_tests(secili: list[str] | None = None, restart: bool = False):
    model_kisa = _aktif_model_kisalt()

    if restart:
        ok = _chancellor_restart()
        if not ok:
            tg_send("⚠️ <b>Chancellor restart başarısız</b> — testler iptal edildi.")
            return

    aktif_testler = [TEST_MAP[s] for s in secili if s in TEST_MAP] if secili else TESTLER
    if not aktif_testler:
        print(f"[SIM] Bilinmeyen test ID'leri: {secili}")
        tg_send(f"⚠️ Bilinmeyen test ID: {secili}")
        return

    toplam   = len(aktif_testler)
    sonuclar = []
    mod_notu = f"--only {','.join(secili)}" if secili else "tümü"
    restart_notu = " · restart ✓" if restart else ""

    tg_send(
        f"⚔️ <b>Simülatör v2.2 Başladı</b>\n"
        f"📋 {toplam} test ({mod_notu}){restart_notu}\n"
        f"🤖 {model_kisa} · test_mode=True (chroma kirletmez)\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    time.sleep(3)

    son_grup = None
    for idx, (tid, grup, mesaj, beklenti, timeout) in enumerate(aktif_testler, 1):
        # Grup değişiminde chancellor restart — context'i temizler
        if restart and grup != son_grup and son_grup is not None:
            print(f"\n[SIM] Grup geçişi ({son_grup} → {grup}) — chancellor restart...")
            _chancellor_restart()
        son_grup = grup
        print(f"\n[{idx}/{toplam}] {tid} ({grup}) — {mesaj[:50]}")
        tg_send(
            f"🧪 <b>[{idx}/{toplam}] {tid}</b> ({grup})\n"
            f"📨 <i>{beklenti}</i>"
        )
        time.sleep(2)

        try:
            baslangic_idx = len(LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines())
        except Exception:
            baslangic_idx = 0

        t_baslangic = time.time()
        inject_message(CHAT_ID, mesaj, test_mode=True)
        print(f"  [INJECT] → '{mesaj[:60]}'")

        yanit = _bekle_inject_sonrasi_out(baslangic_idx, timeout)
        sure  = round(time.time() - t_baslangic, 1)

        if yanit is None:
            sonuclar.append((tid, grup, mesaj, None, [f"❌ TIMEOUT ({timeout}s)"], False))
            tg_send(f"⏱️ <b>{tid}</b> TIMEOUT ({timeout}s)")
            print(f"  [TIMEOUT] {timeout}s")
            # Timeout sonrası stuck processing temizle — sonraki test 500 almasın
            print("[SIM] Timeout — chancellor restart (stuck processing temizle)...")
            _chancellor_restart()
        else:
            gecti, notlar = format_kontrol(yanit)
            sonuclar.append((tid, grup, mesaj, yanit, notlar, gecti))
            durum = "✅" if gecti else "⚠️"
            print(f"  [{durum}] {sure}s | {' | '.join(notlar)}")
            print(f"  YANIT: {yanit[:120]}")

        time.sleep(12)

    # ── ÖZET ──────────────────────────────────────────
    basarili  = sum(1 for *_, gecti in sonuclar if gecti)
    timeout_c = sum(1 for *_, notlar, gecti in sonuclar
                    if any("TIMEOUT" in n for n in notlar))

    rapor = [
        f"⚔️ <b>Simülatör Tamamlandı</b>",
        f"📊 <b>{basarili}/{toplam}</b> PASS · %{int(100*basarili/toplam)}",
        f"⏱️ TIMEOUT: {timeout_c}  |  ❌ FAIL: {toplam-basarili-timeout_c}",
        f"🤖 {model_kisa}  |  {mod_notu}",
        "",
    ]
    for tid, grup, mesaj, yanit, notlar, gecti in sonuclar:
        durum = "✅" if gecti else ("⏱️" if any("TIMEOUT" in n for n in notlar) else "❌")
        sorunlar = [n for n in notlar if n.startswith("❌") or n.startswith("⚠️")]
        satir = f"{durum} <b>{tid}</b> — {mesaj[:35]}"
        if sorunlar:
            satir += f"\n    {' | '.join(sorunlar[:3])}"
        rapor.append(satir)

    tg_send("\n".join(rapor))

    basarisizlar = [(t,g,m,y,n,p) for t,g,m,y,n,p in sonuclar
                    if not p and not any("TIMEOUT" in x for x in n)]
    if basarisizlar:
        detay = ["🔍 <b>Başarısız — Detay:</b>"]
        for tid, grup, mesaj, yanit, notlar, _ in basarisizlar[:5]:
            detay.append(f"\n<b>{tid}</b>: {mesaj[:40]}")
            detay.append(f"Yanıt: {(yanit or 'YOK')[:120]}")
            detay.append(f"❌ {', '.join(n for n in notlar if n.startswith('❌'))}")
        tg_send("\n".join(detay))

    print(f"\n[SIM] Tamamlandı: {basarili}/{toplam} PASS")


if __name__ == "__main__":
    args = sys.argv[1:]

    # --clear: restart chancellor
    restart = "--clear" in args
    args = [a for a in args if a != "--clear"]

    # --only S1,S2,...
    secili = None
    if "--only" in args:
        idx = args.index("--only")
        if idx + 1 < len(args):
            secili = [s.strip() for s in args[idx + 1].split(",")]

    run_tests(secili=secili, restart=restart)
