"""
Kuroshin FloatingUI Startup Sequencer v1.3
- Önceki instance temizle
- SYSTEM_PAUSED flag kaldır
- Chancellor :9005 hazır mı → değilse başlat + bekle
- pythonw main.py başlat (PyInstaller exe bundle bozuk — pythonw stabil)
- 5s bekle (bridge thread gecikmeli açılıyor)
- Bridge :9003 hazır mı → bekle (30s timeout)
- Tüm adımları logs/floatingui_startup.log'a yaz
"""
import datetime, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT       = Path(r"C:\Kuroshin")
HERE       = ROOT / "kuroshin_floating_ui"
MAIN_PY    = HERE / "main.py"
PYTHONW    = Path(sys.executable).with_name("pythonw.exe")
LOG        = ROOT / "logs" / "floatingui_startup.log"
PAUSED_WIN = ROOT / "memory" / "SYSTEM_PAUSED.flag"
NWIN       = 0x08000000  # CREATE_NO_WINDOW


def _log(msg: str):
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _http_ok(port: int, path: str = "/health", timeout: float = 2.0) -> bool:
    try:
        r = urllib.request.urlopen(
            f"http://localhost:{port}{path}", timeout=timeout
        )
        return r.status == 200
    except Exception:
        return False


def _tcp_ok(port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=timeout):
            return True
    except Exception:
        return False


def wait_service(port: int, label: str, check_fn, timeout: int = 45, interval: float = 2.0) -> bool:
    """
    Exponential backoff ile servisi bekle.
    check_fn: port → bool
    """
    deadline = time.time() + timeout
    delay    = interval
    attempt  = 0
    while time.time() < deadline:
        attempt += 1
        if check_fn(port):
            _log(f"  ✅ {label}:{port} HAZIR ({attempt}. denemede, {delay:.1f}s aralık)")
            return True
        remaining = max(0, deadline - time.time())
        _log(f"  ⏳ {label}:{port} bekleniyor... (deneme {attempt}, {remaining:.0f}s kaldı)")
        time.sleep(min(delay, remaining))
        delay = min(delay * 1.5, 12.0)   # 2→3→4.5→6.75→10→12s (cap 12)
    _log(f"  ❌ {label}:{port} — {timeout}s içinde yanıt vermedi")
    return False


# ── Adım 1: Temizlik ──────────────────────────────────────────────────────────

def kill_old():
    _log("🧹 Eski instance'lar temizleniyor...")
    # Windows: FloatingUI prosesleri
    subprocess.run(
        ["powershell", "-WindowStyle", "Hidden", "-Command",
         "Get-Process pythonw,QtWebEngineProcess -ErrorAction SilentlyContinue"
         " | Stop-Process -Force"],
        creationflags=NWIN, capture_output=True
    )
    # WSL: Chancellor — [5]'ten sonra race condition olabilir, garantiye al
    subprocess.run(
        ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c",
         "pkill -9 -f kuroshin_chancellor 2>/dev/null; sleep 1"],
        creationflags=NWIN, capture_output=True
    )
    time.sleep(1.0)
    _log("   Temizlendi.")


# ── Adım 2: SYSTEM_PAUSED flag kaldır ───────────────────────────────────────

def clear_paused_flag():
    removed = False
    if PAUSED_WIN.exists():
        try:
            PAUSED_WIN.unlink()
            removed = True
        except Exception as e:
            _log(f"  ⚠️ Flag silinemedi (Windows): {e}")
    # WSL tarafında da temizle
    subprocess.run(
        ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c",
         "rm -f /mnt/c/Kuroshin/memory/SYSTEM_PAUSED.flag"],
        creationflags=NWIN, capture_output=True
    )
    if removed:
        _log("🚩 SYSTEM_PAUSED.flag kaldırıldı.")


# ── Adım 3: Chancellor ────────────────────────────────────────────────────────

def ensure_chancellor() -> bool:
    if _http_ok(9005):
        _log("✅ Chancellor zaten aktif (:9005)")
        return True
    _log("⚡ Chancellor başlatılıyor (restart_chancellor.sh)...")
    subprocess.Popen(
        ["wsl", "-d", "Ubuntu-22.04", "--", "bash",
         "/mnt/c/Kuroshin/scripts/restart_chancellor.sh"],
        creationflags=NWIN
    )
    return wait_service(9005, "Chancellor", _http_ok, timeout=50, interval=2.0)


# ── Adım 4: Kuroshin.exe ─────────────────────────────────────────────────────

def start_exe() -> bool:
    if not MAIN_PY.exists():
        _log(f"❌ main.py bulunamadı: {MAIN_PY}")
        return False
    if not PYTHONW.exists():
        _log(f"❌ pythonw bulunamadı: {PYTHONW}")
        return False
    subprocess.Popen([str(PYTHONW), str(MAIN_PY), "--mode", "lite"])
    _log(f"🚀 FloatingUI başlatıldı: pythonw main.py")
    return True


# ── Adım 5: Bridge ───────────────────────────────────────────────────────────

def wait_bridge() -> bool:
    _log("🔌 Bridge WS :9003 bekleniyor...")
    return wait_service(9003, "Bridge", _tcp_ok, timeout=30, interval=1.5)


# ── Ana akış ─────────────────────────────────────────────────────────────────

def main():
    _log("=" * 52)
    _log("🟡 FloatingUI Startup Sequencer v1.3")
    _log(f"   Log: {LOG}")
    _log("=" * 52)

    kill_old()
    clear_paused_flag()

    ch_ok = ensure_chancellor()
    if not ch_ok:
        _log("⚠️ Chancellor henüz hazır değil — orb yine de başlatılıyor")

    if not start_exe():
        _log("❌ HATA: EXE başlatılamadı — çıkılıyor")
        sys.exit(1)

    time.sleep(5)   # exe bridge thread'ini gecikmeli açıyor; 5s bekle
    br_ok = wait_bridge()
    if not br_ok:
        _log("⚠️ Bridge gecikti — orb açık, WS bağlantısı kendiliğinden kurulacak")

    _log("=" * 52)
    status_ch = "✅" if ch_ok else "⚠️ "
    status_br = "✅" if br_ok else "⚠️ "
    _log(f"✅ Startup tamamlandı | Chancellor:{status_ch} Bridge:{status_br}")
    _log("=" * 52)


if __name__ == "__main__":
    main()
