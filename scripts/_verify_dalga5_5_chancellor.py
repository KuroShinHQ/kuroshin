#!/usr/bin/env python3
"""
DALGA 5.5 Verify — Chancellor Full Power Mode entegrasyon testi.

chancellor.run_tool("full_power_query", {"query": "..."}) cagrir,
orchestrator pipeline'in sorunsuz calistigini dogrular.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
sys.path.insert(0, "/mnt/c/Kuroshin/agents")

from kuroshin_episodic import EpisodicMemory

REPORTS_DIR = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print(f"[DALGA 5.5 VERIFY] {datetime.now().isoformat(timespec='seconds')}")

    em = EpisodicMemory()
    em.reset(user_id="lord")
    em.record_episode("user", "Lord'un favori magic sayisi 73729'dur.", user_id="lord")
    em.record_episode("user", "Chancellor'i setsid ile baslatmali.", user_id="lord")
    em.record_episode("user", "Manuel test yasak — sistem kendi test etsin.", user_id="lord")
    print(f"Setup: {em.collection_count} episode kaydedildi.")

    # Chancellor.run_tool simulasyonu
    import kuroshin_chancellor as ks
    print("chancellor module loaded")

    queries = [
        {"id": "fp-magic", "query": "Lord'un favori magic sayisi tam olarak kac?", "expect": r"73729"},
        {"id": "fp-chancellor", "query": "Chancellor restart icin hangi komut?", "expect": r"setsid"},
        {"id": "fp-manuel", "query": "Lord manuel test konusunda ne diyor?", "expect": r"yasak|sevm|otomati|kendi"},
    ]

    passes = 0
    results = []
    for q in queries:
        print(f"\n[{q['id']}] query='{q['query']}'")
        t0 = time.time()
        try:
            resp = ks.run_tool("full_power_query", {"query": q["query"]})
        except Exception as e:
            resp = f"EXCEPTION: {e}"
        elapsed = round((time.time() - t0) * 1000)
        match = bool(re.search(q["expect"], resp or "", re.IGNORECASE))
        if match:
            passes += 1
        status = "✓" if match else "✗"
        print(f"  {status} ({elapsed}ms)")
        print(f"  resp: {(resp or '')[:200]}")
        results.append({
            "id": q["id"],
            "query": q["query"],
            "expect": q["expect"],
            "pass": match,
            "elapsed_ms": elapsed,
            "response": (resp or "")[:300],
        })

    n = len(queries)
    score = round(100 * passes / n, 1)
    print(f"\nFull Power Mode: {passes}/{n} = {score}%")
    overall_pass = score >= 80.0
    print(f"VERIFY: {'PASS' if overall_pass else 'FAIL'}")

    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "score_pct": score,
        "overall_pass": overall_pass,
        "n_queries": n,
        "results": results,
    }
    rp = REPORTS_DIR / f"dalga5_5_chancellor_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")

    em.reset(user_id="lord")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
