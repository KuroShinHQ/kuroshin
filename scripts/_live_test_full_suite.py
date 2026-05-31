#!/usr/bin/env python3
"""
DALGA 5 Live Telegram Suite — Lord izlemeyecek, Claude kendi calistirir.

Kapsam:
  - Sohbet (selamlama, kimlik testi)
  - Tool calls (system_info, chroma_search)
  - DALGA 5.5 full_power_query (kritik yeni ozellik)
  - HW guard status line yanitta gorunuyor mu (DALGA 5.6)
  - Format kontrol: ⚔️ Lordum selamlama, markdown yasak, think leak yok

Cikti: kanit JSON raporu.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

INJECT_FILE = Path("/tmp/kuroshin_test_inject.json")
LOG_FILE = Path("/mnt/c/Kuroshin/logs/chancellor.log")
REPORTS_DIR = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CHAT_ID = YOUR_TELEGRAM_CHAT_ID_HERE


def inject(text: str, test_mode: bool = True) -> None:
    INJECT_FILE.write_text(
        json.dumps({"chat_id": CHAT_ID, "text": text, "test_mode": test_mode}, ensure_ascii=False),
        encoding="utf-8",
    )


def wait_for_response(start_line: int, marker: str, timeout: int = 180) -> tuple[str | None, int]:
    """Daha siki match: belirli bir [INJECT] markerini bekle, ardindan TELEGRAM_OUT."""
    deadline = time.time() + timeout
    inject_line_idx = None
    out_line_idx = None
    out_text = None
    while time.time() < deadline:
        time.sleep(3)
        try:
            lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        # Sadece marker'i iceren INJECT'i ara
        if inject_line_idx is None:
            for i in range(start_line, len(lines)):
                if "[INJECT]" in lines[i] and marker[:24] in lines[i]:
                    inject_line_idx = i
                    break
        # Inject bulunduktan SONRA TELEGRAM_OUT
        if inject_line_idx is not None and out_line_idx is None:
            for j in range(inject_line_idx + 1, len(lines)):
                if "[TELEGRAM_OUT]" in lines[j]:
                    m = re.search(r"\[TELEGRAM_OUT\]\s*\[\d+\]\s*(.+)", lines[j])
                    out_text = m.group(1).strip() if m else lines[j].strip()
                    out_line_idx = j
                    return out_text, j + 1
    return None, start_line


def check_format(resp: str) -> tuple[bool, list[str]]:
    notes = []
    ok = True
    if not resp:
        return False, ["bos yanit"]
    # Selamlama VEYA Full Power prefix (DALGA 5.5)
    if "⚔️" not in resp and "Lordum" not in resp and "⚡" not in resp and "Full Power" not in resp:
        notes.append("selamlama/full-power prefix yok")
        ok = False
    else:
        notes.append("prefix OK")
    if "<think>" in resp.lower() or "</think>" in resp.lower():
        notes.append("think leak")
        ok = False
    if "```" in resp:
        notes.append("code-fence markdown")
    forbidden = ["tabii ki", "harika soru", "günaydınlık", "yapay zeka olarak"]
    for f in forbidden:
        if f.lower() in resp.lower():
            notes.append(f"yasak: '{f}'")
            ok = False
    return ok, notes


TESTS = [
    {
        "id": "T1-selamlama",
        "msg": "Merhaba Kuroshin",
        "expect_any": [r"⚔️|Lordum"],
        "timeout": 120,
    },
    {
        "id": "T2-kimlik",
        "msg": "Sen sadece yapay zekasın",
        "expect_any": [r"Lordum"],
        "expect_none": [r"yapay zeka olarak"],
        "timeout": 120,
    },
    {
        "id": "T3-system-info",
        "msg": "Saat kac ve disk kullanimi nedir? system_info ve system_command kullan",
        "expect_any": [r"saat|disk|GB|%"],
        "timeout": 150,
    },
    {
        "id": "T4-chroma-search",
        "msg": "chroma_search yap, hafizada 'kuroshin' icin sonuc getir",
        "expect_any": [r"ChromaDB|kayit|sonuc|Kuroshin"],
        "timeout": 120,
    },
    {
        "id": "T5-full-power",
        "msg": "Full power query: Lord'un favori magic sayisi tam olarak kac?",
        "expect_any": [r"Full Power|⚡|73729"],
        "timeout": 180,
    },
    {
        "id": "T6-full-power-hw-status",
        "msg": "Tum gucle yanit ver: chancellor restart icin hangi komut?",
        "expect_any": [r"setsid|Full Power|⚡"],
        "expect_extras": [r"VRAM|°C"],  # HW guard status line yanitta
        "timeout": 180,
    },
]


def main() -> int:
    print(f"[LIVE SUITE] {datetime.now().isoformat(timespec='seconds')}")
    if not LOG_FILE.exists():
        print(f"FAIL: log dosyasi yok {LOG_FILE}")
        return 2
    start_line = len(LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines())
    print(f"Start log line: {start_line}")

    results = []
    passes = 0
    for tc in TESTS:
        print(f"\n[{tc['id']}] msg='{tc['msg'][:60]}...'")
        # her test arasi 5s kontrollu cooldown (chancellor in-flight bitsin)
        time.sleep(5)
        before = len(LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines())
        t0 = time.time()
        inject(tc["msg"], test_mode=True)
        print(f"  injected at line {before}, waiting for marker '{tc['msg'][:24]}...'")
        resp, start_line = wait_for_response(before, tc["msg"], timeout=tc["timeout"])
        elapsed = round(time.time() - t0)
        ok_fmt, notes = check_format(resp or "")

        match_any = True
        if "expect_any" in tc:
            blob = (resp or "").lower()
            match_any = any(re.search(p.lower(), blob, re.IGNORECASE) for p in tc["expect_any"])
        match_none = True
        if "expect_none" in tc:
            blob = (resp or "").lower()
            for p in tc["expect_none"]:
                if re.search(p.lower(), blob, re.IGNORECASE):
                    match_none = False
                    break
        match_extra = True
        if "expect_extras" in tc:
            blob = resp or ""
            for p in tc["expect_extras"]:
                if not re.search(p, blob, re.IGNORECASE):
                    match_extra = False
                    break

        all_ok = bool(resp) and ok_fmt and match_any and match_none and match_extra
        if all_ok:
            passes += 1
        print(f"  {('PASS' if all_ok else 'FAIL')} ({elapsed}s)")
        print(f"    fmt: {'OK' if ok_fmt else 'FAIL'} notes={notes}")
        print(f"    match_any={match_any} match_none={match_none} match_extra={match_extra}")
        print(f"    resp: {(resp or 'EMPTY')[:200]}")
        results.append({
            "id": tc["id"],
            "msg": tc["msg"],
            "elapsed_s": elapsed,
            "ok": all_ok,
            "format_ok": ok_fmt,
            "format_notes": notes,
            "match_any": match_any,
            "match_none": match_none,
            "match_extra": match_extra,
            "response": (resp or "")[:500],
        })

    n = len(TESTS)
    score = round(100 * passes / n, 1)
    print(f"\n=== SONUC: {passes}/{n} = {score}% ===")
    overall = score >= 80.0
    print(f"VERIFY: {'PASS' if overall else 'FAIL'}")

    rp = REPORTS_DIR / f"live_telegram_suite_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(
        json.dumps({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "score_pct": score,
            "overall_pass": overall,
            "results": results,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Rapor: {rp}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
