#!/usr/bin/env python3
"""
DALGA 5.6 Verify — Hardware Guard live testi.

3 senaryo:
  1) get_hw_status() NVML metric dondurur
  2) safe_for_heavy() normal kosulda True doner
  3) Esik manipulasyon ile safe_for_heavy() False donmeli
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")

from kuroshin_hw_guard import (
    get_hw_status,
    safe_for_heavy,
    short_status_line,
    record_throttle_event,
    VRAM_WARN_MB,
    TEMP_WARN_C,
)

REPORTS_DIR = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print(f"[DALGA 5.6 VERIFY] {datetime.now().isoformat(timespec='seconds')}")

    # T1: status getirilebiliyor mu
    s = get_hw_status()
    t1 = bool(s.get("available")) and "vram_used_mb" in s and "temp_c" in s
    print(f"T1 status retrievable: {'✓' if t1 else '✗'}  -> {s}")

    # T2: status_line formatli
    line = short_status_line()
    t2 = "VRAM" in line and "°C" in line
    print(f"T2 status_line ok: {'✓' if t2 else '✗'}  -> {line}")

    # T3: safe_for_heavy normalde True dommeli (sistem yarisini bile kullanmiyor)
    ok, reason = safe_for_heavy()
    t3 = ok and reason in ("ok",)
    print(f"T3 safe_for_heavy normal: {'✓' if t3 else '✗'}  -> ok={ok} reason='{reason}'")

    # T4: reserve_mb artirildiginda eşik kasıtlı tetiklenir (negative test)
    very_high_reserve = VRAM_WARN_MB  # esige esit reserve = mevcut kullanim ile false vermeli
    ok2, reason2 = safe_for_heavy(reserve_mb=very_high_reserve)
    t4 = (not ok2) and "VRAM" in reason2
    print(f"T4 safe_for_heavy negative test: {'✓' if t4 else '✗'}  -> ok={ok2} reason='{reason2}'")

    # T5: event log yazilabiliyor
    log_path = Path("/root/kuroshin/logs/hw_throttle_events.jsonl")
    before = log_path.stat().st_size if log_path.exists() else 0
    record_throttle_event("dalga5_6_verify_test")
    after = log_path.stat().st_size if log_path.exists() else 0
    t5 = after > before
    print(f"T5 event log writeable: {'✓' if t5 else '✗'}  -> {after - before} byte eklendi")

    # T6: chancellor full_power_query pre-check entegrasyonu kodda var
    chancellor_path = Path("/mnt/c/Kuroshin/agents/kuroshin_chancellor.py")
    content = chancellor_path.read_text(encoding="utf-8", errors="ignore")
    t6 = "from kuroshin_hw_guard import safe_for_heavy" in content and "FULL_POWER BLOCKED" in content
    print(f"T6 chancellor pre-check integrated: {'✓' if t6 else '✗'}")

    passes = sum([t1, t2, t3, t4, t5, t6])
    n = 6
    score = round(100 * passes / n, 1)
    print(f"\nHardware Guard: {passes}/{n} = {score}%")
    overall = score >= 80.0
    print(f"VERIFY: {'PASS' if overall else 'FAIL'}")

    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "score_pct": score,
        "overall_pass": overall,
        "status": s,
        "tests": {
            "T1_status_retrievable": t1,
            "T2_status_line_format": t2,
            "T3_safe_normal": t3,
            "T4_safe_negative": t4,
            "T5_event_log": t5,
            "T6_chancellor_integration": t6,
        },
    }
    rp = REPORTS_DIR / f"dalga5_6_hw_guard_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
