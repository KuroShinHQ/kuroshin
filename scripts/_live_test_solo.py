#!/usr/bin/env python3
"""Tek-test live inject + iyilesmis marker matching."""
from __future__ import annotations
import json, re, sys, time
from datetime import datetime
from pathlib import Path

INJECT_FILE = Path("/tmp/kuroshin_test_inject.json")
LOG_FILE = Path("/mnt/c/Kuroshin/logs/chancellor.log")
CHAT_ID = YOUR_TELEGRAM_CHAT_ID_HERE


def inject(text: str) -> None:
    INJECT_FILE.write_text(
        json.dumps({"chat_id": CHAT_ID, "text": text, "test_mode": True}, ensure_ascii=False),
        encoding="utf-8",
    )


def run_one(msg: str, timeout: int = 180) -> tuple[bool, str, int]:
    lines_before = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = len(lines_before)
    marker_substr = msg[:28]
    print(f"[t={datetime.now():%H:%M:%S}] inject (line {start})  '{marker_substr}...'")
    inject(msg)
    t0 = time.time()
    deadline = t0 + timeout
    inject_idx = None
    while time.time() < deadline:
        time.sleep(3)
        lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        # 1) bulunmamissa inject satirini ara
        if inject_idx is None:
            for i in range(start, len(lines)):
                if "[INJECT]" in lines[i] and marker_substr in lines[i]:
                    inject_idx = i
                    print(f"  inject seen at line {i} (+{round(time.time()-t0)}s)")
                    break
        # 2) inject sonrasi ilk TELEGRAM_OUT
        if inject_idx is not None:
            for j in range(inject_idx + 1, len(lines)):
                if "[TELEGRAM_OUT]" in lines[j]:
                    m = re.search(r"\[TELEGRAM_OUT\]\s*\[\d+\]\s*(.+)", lines[j])
                    text = m.group(1).strip() if m else lines[j].strip()
                    elapsed = round(time.time() - t0)
                    return True, text, elapsed
    return False, "", round(time.time() - t0)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _live_test_solo.py 'message' [timeout]")
        return 2
    msg = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 180
    ok, resp, elapsed = run_one(msg, timeout)
    print(f"\n{'PASS' if ok else 'TIMEOUT'} (after {elapsed}s)")
    print(f"resp: {(resp or 'EMPTY')[:400]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
