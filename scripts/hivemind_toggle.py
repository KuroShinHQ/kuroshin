#!/usr/bin/env python3
"""
Kuroshin Hivemind Toggle v1.0
Hivemind agent memory entegrasyonunu açar/kapatır.

Kullanım:
  python hivemind_toggle.py on|off|status|boot

UYARI: HIVEMIND_ENABLED=true yapılırsa session traces Deeplake cloud'a gider.
Kuroshin doktrinini korumak için varsayılan olarak kapalı bırakın.
"""

import sys
import os
import re
import subprocess
import socket
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
KUROSHIN_ROOT = Path(r"C:\Kuroshin")
ENV_FILE      = KUROSHIN_ROOT / ".env"
LOG_FILE      = KUROSHIN_ROOT / "logs" / "hivemind_toggle.log"

# ── Logging ────────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── Telegram ───────────────────────────────────────────────────────────────
def _tg_credentials():
    if not ENV_FILE.exists():
        return None, None
    try:
        content = ENV_FILE.read_text(encoding="utf-8")
        tok = re.search(r'^TELEGRAM_TOKEN\s*=\s*(.+)$', content, re.MULTILINE)
        cid = re.search(r'^TELEGRAM_CHAT_ID\s*=\s*(.+)$', content, re.MULTILINE)
        return (
            tok.group(1).strip() if tok else None,
            cid.group(1).strip() if cid else None,
        )
    except Exception:
        return None, None

def send_telegram(msg: str):
    # IPv4 bypass — WSL'de IPv6 DNS çözümü Telegram'a bağlanamıyor
    _orig = socket.getaddrinfo
    def _ipv4(host, port, family=0, *a, **kw):
        return _orig(host, port, socket.AF_INET, *a, **kw)
    socket.getaddrinfo = _ipv4
    try:
        token, chat_id = _tg_credentials()
        if not token or not chat_id:
            _log("[TG] Credentials bulunamadı, bildirim atlanıyor")
            return
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML",
        }).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data,
            timeout=10,
        )
        _log("[TG] Bildirim gönderildi")
    except Exception as e:
        _log(f"[TG] Bildirim hatası: {e}")
    finally:
        socket.getaddrinfo = _orig

# ── .env Okuma / Yazma ─────────────────────────────────────────────────────
def read_env() -> dict:
    if not ENV_FILE.exists():
        return {}
    env_vars = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, val = line.partition('=')
            env_vars[key.strip()] = val.strip()
    return env_vars

def write_env(updates: dict):
    """
    Mevcut .env içeriğini koruyarak belirtilen key'leri güncelle.
    Dosyada olmayan key'ler sona eklenir.
    """
    if not ENV_FILE.exists():
        _log(f"[ENV] {ENV_FILE} bulunamadı")
        return False

    original_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = []
    updated_keys = set()

    for line in original_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Dosyada olmayan key'leri sona ekle
    missing = {k: v for k, v in updates.items() if k not in updated_keys}
    if missing:
        new_lines.append("")
        for key, val in missing.items():
            new_lines.append(f"{key}={val}")

    ENV_FILE.write_text('\n'.join(new_lines) + '\n', encoding="utf-8")
    return True

def get_state() -> dict:
    env = read_env()
    return {
        "enabled": env.get("HIVEMIND_ENABLED", "false").lower() == "true",
        "capture": env.get("HIVEMIND_CAPTURE", "false").lower() == "true",
    }

# ── Hivemind CLI ───────────────────────────────────────────────────────────
# Windows'ta npm global binary'leri .cmd uzantılıdır — shell=True gerekir
def is_installed() -> bool:
    try:
        r = subprocess.run(
            "hivemind --version",
            capture_output=True, text=True, timeout=5, shell=True,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def run_install() -> bool:
    if not is_installed():
        _log("[HIVEMIND] CLI kurulu değil — npm install -g @deeplake/hivemind gerekli")
        return False
    try:
        _log("[HIVEMIND] 'hivemind install --only claude' çalıştırılıyor...")
        r = subprocess.run(
            "hivemind install --only claude",
            capture_output=True, text=True, timeout=60, shell=True,
        )
        if r.returncode == 0:
            _log("[HIVEMIND] Install başarılı")
            return True
        _log(f"[HIVEMIND] Install başarısız: {r.stderr[:300]}")
        return False
    except Exception as e:
        _log(f"[HIVEMIND] Install hatası: {e}")
        return False

# ── Komutlar ───────────────────────────────────────────────────────────────
def cmd_on():
    state = get_state()
    if state["enabled"]:
        _log("[HIVEMIND] Zaten aktif")
        send_telegram("ℹ️ <b>Hivemind</b> zaten aktif durumda.")
        return

    _log("[HIVEMIND] Aktif ediliyor...")
    write_env({"HIVEMIND_ENABLED": "true", "HIVEMIND_CAPTURE": "true"})
    installed_ok = run_install()

    send_telegram(
        "⚠️ <b>Hivemind AKTİF EDİLDİ</b>\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "🔄 HIVEMIND_CAPTURE: true\n"
        "⚠️ Session traces artık Deeplake'e gidiyor!\n"
        + ("✅ hivemind install tamamlandı\n" if installed_ok else "⚠️ Hivemind CLI kurulu değil\n")
        + "\nKapatmak için: /hivemind_kapat"
    )
    _log("[HIVEMIND] Aktif edildi — Deeplake veri akışı başladı")

def cmd_off():
    state = get_state()
    if not state["enabled"]:
        _log("[HIVEMIND] Zaten kapalı")
        send_telegram("ℹ️ <b>Hivemind</b> zaten kapalı durumda.")
        return

    _log("[HIVEMIND] Devre dışı bırakılıyor...")
    write_env({"HIVEMIND_ENABLED": "false", "HIVEMIND_CAPTURE": "false"})

    send_telegram(
        "🛡️ <b>Hivemind DEVRE DIŞI</b>\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "🔒 HIVEMIND_CAPTURE: false\n"
        "✅ Kuroshin doktrinini koruma aktif\n"
        "📌 Deeplake veri akışı durduruldu"
    )
    _log("[HIVEMIND] Devre dışı — Kuroshin korunuyor")

def cmd_status():
    state = get_state()
    inst = is_installed()
    lines = [
        "=== HIVEMIND DURUMU ===",
        f"HIVEMIND_ENABLED : {'✅ true' if state['enabled'] else '❌ false'}",
        f"HIVEMIND_CAPTURE : {'⚠️  true  (veri akışı var!)' if state['capture'] else '🔒 false'}",
        f"CLI Kurulum      : {'✅ kurulu' if inst else '❌ kurulu değil'}",
        f"Doktrin Durumu   : {'⚠️  AÇIK — Deeplake veri alıyor' if state['enabled'] else '🛡️  KAPALI — Kuroshin korunuyor'}",
        "=======================",
    ]
    print('\n'.join(lines))

def cmd_boot():
    """
    Kuroshin.bat'tan çağrılır.
    HIVEMIND_ENABLED=true ise install çalıştırır; false ise sessizce çıkar.
    """
    state = get_state()
    if state["enabled"]:
        _log("[HIVEMIND] Boot hook: ENABLED=true — install çalıştırılıyor")
        run_install()
    else:
        _log("[HIVEMIND] Boot hook: ENABLED=false — Kuroshin doktrinini korunuyor, atlanıyor")

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Kullanım: python hivemind_toggle.py on|off|status|boot")
        print()
        cmd_status()
        return

    cmd = sys.argv[1].strip().lower()

    if cmd in ("on", "ac", "aktif", "true", "1"):
        cmd_on()
    elif cmd in ("off", "kapat", "deaktif", "false", "0"):
        cmd_off()
    elif cmd in ("status", "durum"):
        cmd_status()
    elif cmd == "boot":
        cmd_boot()
    else:
        print(f"Bilinmeyen komut: {cmd}")
        print("Geçerli komutlar: on | off | status | boot")
        sys.exit(1)

if __name__ == "__main__":
    main()
