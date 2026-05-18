"""
Kuroshin Ortak Yardımcılar — kuroshin_utils.py
================================================
Tüm servisler buradan import eder:
  - setup_logger()   : RotatingFileHandler, 5MB/7gün
  - send_telegram()  : Telegram mesaj gönder (chunked)
  - estimate_vram()  : GGUF dosya adından GB tahmini
"""

import os
import logging
import requests
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/mnt/c/Kuroshin/.env"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
MAX_MSG_LEN    = 4000


def setup_logger(name: str, log_path: str | Path, level=logging.INFO) -> logging.Logger:
    """5MB + 3 backup, INFO level. Hem dosyaya hem stdout'a yazar."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def send_telegram(text: str, chat_id: int | None = None, token: str | None = None) -> bool:
    """Telegram'a mesaj gönder. Uzun mesajları MAX_MSG_LEN'e böler."""
    _token = token or TELEGRAM_TOKEN
    _chat  = chat_id or TELEGRAM_CHAT
    if not _token or not _chat:
        return False
    url = f"https://api.telegram.org/bot{_token}/sendMessage"
    chunks = [text[i:i + MAX_MSG_LEN] for i in range(0, max(len(text), 1), MAX_MSG_LEN)]
    ok = True
    for chunk in chunks:
        try:
            r = requests.post(url, json={"chat_id": _chat, "text": chunk, "parse_mode": "HTML"}, timeout=10)
            if not r.ok:
                ok = False
        except Exception:
            ok = False
    return ok


def estimate_vram(filename: str) -> float:
    """GGUF dosya adından VRAM tahmini (GB). Bulunamazsa 0.0 döner."""
    import re
    name = filename.lower()
    # Parametre sayısı (ör: 7b, 14b, 1.5b)
    m = re.search(r"(\d+\.?\d*)b", name)
    params = float(m.group(1)) if m else 0.0
    # Quantizasyon türü
    quant_map = {
        "q2_k": 0.32, "q3_k": 0.38, "q4_0": 0.50, "q4_k": 0.55,
        "q4_k_m": 0.55, "q4_k_s": 0.52, "q5_0": 0.63, "q5_k": 0.65,
        "q5_k_m": 0.65, "q6_k": 0.75, "q8_0": 1.00, "f16": 2.00,
    }
    bits = 0.55  # default q4_k_m
    for k, v in quant_map.items():
        if k in name:
            bits = v
            break
    if params <= 0:
        return 0.0
    return round(params * bits, 1)
