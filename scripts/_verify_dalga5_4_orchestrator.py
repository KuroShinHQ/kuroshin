#!/usr/bin/env python3
"""
DALGA 5.4 Verify — LangGraph Orchestrator vs single-agent baseline karsilastir.

5 test query: Kuroshin context'ine ozel fact (RAG'dan veya Episodic'ten cekilir).
Baseline (sadece LLM): cogu zaman hallucinate eder.
Multi-agent (LangGraph): RAG/Episodic'den dogru fact gelir.

Metrik: kalite (fact match) + wall-clock.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_orchestrator import baseline_single_agent, run as run_orchestrator
from kuroshin_episodic import EpisodicMemory

REPORTS_DIR = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# Test setup: episodic'e bilinen fact'ler ekle, sonra sor
SETUP_EPISODES = [
    ("user", "Lord'un favori magic sayisi 73729'dur."),
    ("user", "Chancellor'i setsid ile baslatmali, nohup yetmiyor."),
    ("user", "Manuel test yasak — sistem kendi test etsin (Lord kurali)."),
    ("user", "Kahveyi sutsuz iciyorum, asla seker eklemiyorum."),
    ("user", "Dalga 5.1 ile context 16K -> 256K yukseltildi."),
]

QUERIES = [
    {
        "id": "q1-magic",
        "query": "Lord'un favori magic sayisi tam olarak kac?",
        "expect_regex": r"73729",
    },
    {
        "id": "q2-chancellor",
        "query": "Chancellor restart icin hangi komut kullanilmali?",
        "expect_regex": r"setsid",
    },
    {
        "id": "q3-rule",
        "query": "Lord manuel test konusunda ne diyor?",
        "expect_regex": r"yasak|sevm|otomati|kendi",
    },
    {
        "id": "q4-coffee",
        "query": "Lord'un kahve tercihi nedir?",
        "expect_regex": r"suts|sütsüz|seker|şeker yok|şekersiz",
    },
    {
        "id": "q5-context",
        "query": "Hangi dalga ile context buyutuldu ve hangi degere?",
        "expect_regex": r"5\.1|256|262",
    },
]


def main() -> int:
    print(f"[DALGA 5.4 VERIFY] {datetime.now().isoformat(timespec='seconds')}")

    # Episodic setup
    em = EpisodicMemory()
    em.reset(user_id="lord")
    for role, content in SETUP_EPISODES:
        em.record_episode(role, content, user_id="lord")
    print(f"Setup: {em.collection_count} episode kaydedildi.")

    results = []
    baseline_pass = 0
    orch_pass = 0
    baseline_total_ms = 0
    orch_total_ms = 0

    for q in QUERIES:
        print(f"\n[{q['id']}] {q['query']}")

        b = baseline_single_agent(q["query"])
        b_match = bool(re.search(q["expect_regex"], b["final_answer"] or "", re.IGNORECASE))
        baseline_total_ms += b["metrics"]["total_ms"]
        if b_match:
            baseline_pass += 1
        print(f"  baseline ({b['metrics']['total_ms']}ms) match={'✓' if b_match else '✗'} ans='{(b['final_answer'] or '')[:120]}'")

        o = run_orchestrator(q["query"])
        ans = o.get("final_answer") or ""
        o_match = bool(re.search(q["expect_regex"], ans, re.IGNORECASE))
        orch_total_ms += o.get("metrics", {}).get("total_ms", 0)
        if o_match:
            orch_pass += 1
        print(f"  multi-agent ({o.get('metrics',{}).get('total_ms',0)}ms) match={'✓' if o_match else '✗'} ans='{ans[:120]}'")
        print(f"  rag={len(o.get('rag_results') or [])} ep={len(o.get('episodic_results') or [])}")

        results.append({
            "id": q["id"],
            "query": q["query"],
            "expect_regex": q["expect_regex"],
            "baseline_pass": b_match,
            "baseline_ms": b["metrics"]["total_ms"],
            "baseline_answer": (b["final_answer"] or "")[:200],
            "orchestrator_pass": o_match,
            "orchestrator_ms": o.get("metrics", {}).get("total_ms", 0),
            "orchestrator_answer": ans[:200],
            "rag_count": len(o.get("rag_results") or []),
            "episodic_count": len(o.get("episodic_results") or []),
        })

    n = len(QUERIES)
    base_pct = round(100 * baseline_pass / n, 1)
    orch_pct = round(100 * orch_pass / n, 1)
    print(f"\n=== SONUC ===")
    print(f"Baseline (single-agent) :  {baseline_pass}/{n} = {base_pct}%  (toplam {baseline_total_ms:.0f}ms)")
    print(f"Multi-agent (LangGraph) :  {orch_pass}/{n} = {orch_pct}%  (toplam {orch_total_ms:.0f}ms)")
    delta = round(orch_pct - base_pct, 1)
    print(f"Kalite delta: {delta:+.1f} pp")

    overall_pass = orch_pct >= 80.0 and delta >= 20.0  # multi-agent baseline'dan EN AZ %20 daha iyi olmali
    print(f"VERIFY: {'PASS' if overall_pass else 'FAIL'}")

    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "baseline_score": base_pct,
        "orchestrator_score": orch_pct,
        "kalite_delta_pp": delta,
        "baseline_total_ms": baseline_total_ms,
        "orchestrator_total_ms": orch_total_ms,
        "overall_pass": overall_pass,
        "results": results,
    }
    rp = REPORTS_DIR / f"dalga5_4_orchestrator_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")

    em.reset(user_id="lord")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
