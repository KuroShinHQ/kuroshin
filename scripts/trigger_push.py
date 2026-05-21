#!/usr/bin/env python3
"""
Manuel push tetikleyici — chancellor'ın push onay klavyesini doğrudan gönderir.
Chancellor callback'i kendi döngüsünde yakalar ve push'u gerçekleştirir.
Kullanım: python3 trigger_push.py "commit mesajı"
"""
import sys, os, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/mnt/c/Kuroshin/.env"))

TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
TG      = f"https://api.telegram.org/bot{TOKEN}"
GH_TOKEN = os.getenv("GITHUB_TOKEN", "")

commit_msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
    "Kuroshin v8.9.0 — FAZ A/C/D tamamlandi, bug fixler, test iyilestirmeleri"

GIT_DIR = "/mnt/c/Kuroshin"
REPO    = "KuroShinHQ/KuroShinHQ"

# Chancellor'ın okuması için pending push durumunu dosyaya yaz
pending = {"msg": commit_msg, "repo": REPO, "dir": GIT_DIR, "token": GH_TOKEN, "force": False}
Path("/tmp/kuroshin_pending_push.json").write_text(json.dumps(pending, ensure_ascii=False))

# Telegram'a onay klavyesi gönder — chancellor github_push_onayla callback'ini yakalar
r = requests.post(f"{TG}/sendMessage", json={
    "chat_id": CHAT_ID,
    "text": (
        f"⚠️ <b>GitHub Push Onayı</b>\n"
        f"Repo: <code>{REPO}</code>\n"
        f"Commit: <code>{commit_msg[:80]}</code>\n"
        f"Onaylıyor musunuz?"
    ),
    "parse_mode": "HTML",
    "reply_markup": {"inline_keyboard": [[
        {"text": "✅ Onayla", "callback_data": "github_push_onayla"},
        {"text": "❌ İptal",  "callback_data": "github_push_iptal"}
    ]]}
}, timeout=10)

ok = r.json().get("ok", False)
print(f"✅ Onay klavyesi Telegram'a gönderildi: {ok}")
print(f"Commit: {commit_msg}")
print("Chancellor callback'i yakalayıp push'u gerçekleştirecek.")
