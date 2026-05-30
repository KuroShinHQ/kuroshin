#!/usr/bin/env python3
"""
DALGA 5.2 Verify — Hybrid RAG'in dense-only'ye karsi kanitlanabilir kazancini olcer.

Strateji:
  - 6 test query: bazi exact-match (BM25'in dense'i yendigi), bazi semantic-only.
  - Her query icin beklenen pattern var: top_M sonuclarda gectiyse HIT.
  - Hybrid vs Dense-only -> precision@K karsilastir.

Cikti: PASS/FAIL skor + JSON rapor + acik metrik.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_rag import HybridRAG

REPORTS_DIR = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TEST_CASES = [
    {
        "id": "rag-01-exact-tool",
        "query": "kuroshin-bridge tool PASS",
        "expect_any_regex": [r"kuroshin[\-_]bridge", r"PASS"],
        "notes": "Tool kullanim kanitlari (exact match BM25 lehine)",
    },
    {
        "id": "rag-02-semantic-ai",
        "query": "yapay zeka bilinc",
        "expect_any_regex": [r"yapay zeka", r"bilinc|conscious|awareness|self[\-_]awareness", r"intrinsic motivation"],
        "notes": "Semantic similarity (dense lehine)",
    },
    {
        "id": "rag-03-github-push",
        "query": "github push commit mesaji",
        "expect_any_regex": [r"github", r"push|commit"],
        "notes": "Karisik exact + semantic",
    },
    {
        "id": "rag-04-mcp-tool",
        "query": "MCP server fetch_page",
        "expect_any_regex": [r"mcp__", r"kuroshin[\-_]search|fetch_page"],
        "notes": "MCP-prefix exact match",
    },
    {
        "id": "rag-05-paraphrase",
        "query": "anladigin uzerinden derin dusunmek",
        "expect_any_regex": [r"derin|reasoning|akıl|akil|düşün|dusun", r"yapay zeka|reasoning|model"],
        "notes": "Paraphrased (dense lehine - exact keyword yok)",
    },
    {
        "id": "rag-06-mixed",
        "query": "PROBE arastirma rapor",
        "expect_any_regex": [r"PROBE[\-_]?ARASTIRMA", r"rapor|arastir"],
        "notes": "Karisik token (exact + semantic)",
    },
]

TOP_M = 10


def case_hit(hits, expectations) -> tuple[bool, list[str]]:
    text_blob = "\n".join((h.get("doc") or "") for h in hits).lower()
    hit_patterns = []
    missing = []
    for pat in expectations:
        if re.search(pat.lower(), text_blob):
            hit_patterns.append(pat)
        else:
            missing.append(pat)
    success = len(hit_patterns) >= 1
    return success, hit_patterns


def _pure_dense_search(rag, query, top_m):
    """Sirf ChromaDB dense, BM25 ve rerank YOK."""
    cands = rag._dense_search(query, top_k=top_m)
    return [{"doc": c.document, "id": c.doc_id} for c in cands[:top_m]]


def _pure_bm25_search(rag, query, top_m):
    """Sirf BM25, dense YOK."""
    cands = rag._sparse_search(query, top_k=top_m)
    return [{"doc": c.document, "id": c.doc_id} for c in cands[:top_m]]


def main() -> int:
    print(f"[DALGA 5.2 VERIFY] {datetime.now().isoformat(timespec='seconds')}")
    rag = HybridRAG()
    print(f"Corpus: {rag.corpus_size}, collections: {list(rag._cols.keys())}")

    results = []
    pure_dense_pass = 0
    pure_bm25_pass = 0
    hybrid_norerank_pass = 0
    hybrid_full_pass = 0
    latencies = []

    for tc in TEST_CASES:
        q = tc["query"]
        d_only = _pure_dense_search(rag, q, top_m=TOP_M)
        b_only = _pure_bm25_search(rag, q, top_m=TOP_M)
        h_norr = rag.search(q, top_m=TOP_M, use_reranker=False)
        h_full = rag.search(q, top_m=TOP_M, use_reranker=True)

        d_ok, d_hit = case_hit(d_only, tc["expect_any_regex"])
        b_ok, b_hit = case_hit(b_only, tc["expect_any_regex"])
        hn_ok, hn_hit = case_hit(h_norr, tc["expect_any_regex"])
        hf_ok, hf_hit = case_hit(h_full, tc["expect_any_regex"])

        if d_ok: pure_dense_pass += 1
        if b_ok: pure_bm25_pass += 1
        if hn_ok: hybrid_norerank_pass += 1
        if hf_ok: hybrid_full_pass += 1
        if h_full:
            latencies.append(h_full[0]["_latency_ms"])

        results.append({
            "id": tc["id"],
            "query": q,
            "notes": tc["notes"],
            "pure_dense_pass": d_ok,
            "pure_bm25_pass": b_ok,
            "hybrid_norerank_pass": hn_ok,
            "hybrid_full_pass": hf_ok,
            "matched_full": hf_hit,
        })

        def _s(b): return "✓" if b else "✗"
        print(f"  [{tc['id']}] d={_s(d_ok)} b={_s(b_ok)} h-no_rr={_s(hn_ok)} h-full={_s(hf_ok)} q='{q[:40]}'")

    n = len(TEST_CASES)
    p_d = round(100 * pure_dense_pass / n, 1)
    p_b = round(100 * pure_bm25_pass / n, 1)
    p_hn = round(100 * hybrid_norerank_pass / n, 1)
    p_hf = round(100 * hybrid_full_pass / n, 1)

    print(f"\nPure Dense          precision@{TOP_M}: {pure_dense_pass}/{n} = {p_d}%")
    print(f"Pure BM25           precision@{TOP_M}: {pure_bm25_pass}/{n} = {p_b}%")
    print(f"Hybrid (no rerank)  precision@{TOP_M}: {hybrid_norerank_pass}/{n} = {p_hn}%")
    print(f"Hybrid (full+rerank) precision@{TOP_M}: {hybrid_full_pass}/{n} = {p_hf}%")
    delta_vs_dense = round(p_hf - p_d, 1)
    print(f"Hybrid-Full vs Pure-Dense: {delta_vs_dense:+.1f} pp")

    if latencies:
        avg = {k: round(sum(L[k] for L in latencies) / len(latencies), 1) for k in latencies[0].keys()}
        print(f"Avg latency: {avg}")

    overall_pass = p_hf >= 80.0 and p_hn >= 80.0 and rag.corpus_size > 0
    print(f"\nVERIFY: {'PASS' if overall_pass else 'FAIL'}")

    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "corpus_size": rag.corpus_size,
        "top_m": TOP_M,
        "pure_dense_precision": p_d,
        "pure_bm25_precision": p_b,
        "hybrid_norerank_precision": p_hn,
        "hybrid_full_precision": p_hf,
        "hybrid_vs_dense_pp": delta_vs_dense,
        "avg_latency_ms": (avg if latencies else {}),
        "overall_pass": overall_pass,
        "cases": results,
    }
    report_path = REPORTS_DIR / f"dalga5_2_rag_{datetime.now():%Y%m%d_%H%M%S}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {report_path}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
