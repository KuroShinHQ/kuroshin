#!/usr/bin/env python3
"""
Episodic WRITE+READ live test (1 Haz 2026 — DALGA 5.3 entegrasyon kaniti).

Plan:
  1. Baseline: episodic count = 0 (purge sonrasi)
  2. INJECT 1 (test_mode=False) — fact tanit: "Lord magic 86421"
  3. Wait for [EPISODIC] tur kaydedildi log + count artisi (~ 2 entry)
  4. INJECT 2 (test_mode=False) — sor: "Lord magic kac"
  5. Yanit 86421 icermeli + [EPISODIC] context n=N log gozukmeli
"""
from __future__ import annotations
import json, sys, time, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_episodic import EpisodicMemory

INJECT = Path("/tmp/kuroshin_test_inject.json")
LOG    = Path("/mnt/c/Kuroshin/logs/chancellor.log")
CHAT_ID = YOUR_TELEGRAM_CHAT_ID_HERE
FACT_NUM = "86421"
REPORTS = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")


def inject(text: str, test_mode: bool = False):
    INJECT.write_text(
        json.dumps({"chat_id": CHAT_ID, "text": text, "test_mode": test_mode}, ensure_ascii=False),
        encoding="utf-8",
    )


def wait_log_marker(start_line: int, marker_re: str, timeout: int = 180) -> tuple[int, str]:
    """Belirli regex log satirini bekle. (line_idx, match_text) veya (-1, '')."""
    pat = re.compile(marker_re)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        lines = LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i in range(start_line, len(lines)):
            if pat.search(lines[i]):
                return i, lines[i]
    return -1, ""


def main():
    em = EpisodicMemory()
    base = em.collection_count
    print(f"baseline episodic count: {base}")

    start_line = len(LOG.read_text(encoding="utf-8", errors="ignore").splitlines())

    # === INJECT 1 — FACT TANIT (gercek mod, write tetikleyici) ===
    msg1 = f"Lordumun yeni magic sayisi {FACT_NUM}. Bunu hatirla."
    print(f"\n[INJECT 1] {msg1}")
    inject(msg1, test_mode=False)
    out_line, out_txt = wait_log_marker(start_line, r"\[TELEGRAM_OUT\] \[\d+\]", timeout=180)
    if out_line < 0:
        print("FAIL: inject 1 TELEGRAM_OUT yok")
        return 1
    print(f"  out: {out_txt[:160]}")

    # WRITE log'u bekle (post-reply daemon thread)
    write_line, write_txt = wait_log_marker(out_line, r"\[EPISODIC\] tur kaydedildi", timeout=30)
    if write_line < 0:
        print("FAIL: [EPISODIC] tur kaydedildi log yok")
        return 1
    print(f"  write: {write_txt[-80:]}")

    # Kucuk gecikme (chromadb commit) + count artisi
    time.sleep(3)
    after1 = em.collection_count
    delta1 = after1 - base
    print(f"  episodic count: {base} -> {after1} (Δ={delta1})")
    if delta1 < 2:
        print(f"FAIL: beklenen +2 (user+assistant), aldigi +{delta1}")
        return 1

    # === INJECT 2 — RECALL (READ episodic) ===
    start_line2 = len(LOG.read_text(encoding="utf-8", errors="ignore").splitlines())
    msg2 = "Lordumun magic sayisi neydi tam olarak?"
    print(f"\n[INJECT 2] {msg2}")
    inject(msg2, test_mode=False)
    out2_line, out2_txt = wait_log_marker(start_line2, r"\[TELEGRAM_OUT\] \[\d+\]", timeout=180)
    if out2_line < 0:
        print("FAIL: inject 2 TELEGRAM_OUT yok")
        return 1
    print(f"  out: {out2_txt[:200]}")

    # FACT geri geldi mi?
    recalled = FACT_NUM in out2_txt
    # READ log'u var mi
    epi_ctx_line = -1
    lines = LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i in range(start_line2, len(lines)):
        if "[EPISODIC] context n=" in lines[i]:
            epi_ctx_line = i
            print(f"  read: {lines[i][-80:]}")
            break

    print(f"\n=== SONUC ===")
    print(f"  WRITE: Δ={delta1} ({'PASS' if delta1>=2 else 'FAIL'})")
    print(f"  READ context log: {'PASS' if epi_ctx_line>=0 else 'YOK (esik 0.45 alti olabilir)'}")
    print(f"  RECALL fact in reply: {'PASS' if recalled else 'FAIL'}")
    overall = (delta1 >= 2) and recalled
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")

    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "baseline_count": base,
        "after_write_count": after1,
        "write_delta": delta1,
        "fact_num": FACT_NUM,
        "msg1_out_preview": out_txt[:240],
        "msg2_out_preview": out2_txt[:320],
        "read_context_log_found": epi_ctx_line >= 0,
        "recall_fact_in_reply": recalled,
        "overall_pass": overall,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    rp = REPORTS / f"episodic_write_live_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
