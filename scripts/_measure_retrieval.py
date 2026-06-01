#!/usr/bin/env python3
"""
Retrieval Kalite Ölçüm Harness (1 Haz 2026) — observability + entegrasyon kararı.

Soru: chancellor'ın normal yolundaki _get_chroma_context TOP-3 kullanıyor.
      Hybrid RAG (BM25+Dense+RRF+rerank) bu TOP-3'te düz Dense'i GEÇİYOR MU?
      (5.2 verify top-10'da ölçtü → ayırt edici değil. Bu harness TOP-3.)

Metrik: precision@3 (beklenen pattern top-3'te mi) + latency.
Karar:  hybrid_full_p3 >= dense_p3 + MARGIN ise entegrasyon değer; değilse net-negatif.

Salt-okuma, prod'a dokunmaz. Kalıcı regresyon/karar muhafızı.
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_rag import HybridRAG

REPORTS_DIR = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TOP_K = 3            # chancellor _get_chroma_context gerçekte 3 kullanır
INTEGRATION_MARGIN = 0.0  # hybrid en az dense kadar olmalı (latency maliyeti var)

TEST_CASES = [
    {"id": "r-exact-tool",   "query": "kuroshin-bridge tool PASS",            "expect": [r"kuroshin[\-_]bridge|PASS"]},
    {"id": "r-semantic-ai",  "query": "yapay zeka bilinc",                    "expect": [r"yapay zeka|bilinc|conscious|awareness|intrinsic"]},
    {"id": "r-github",       "query": "github push commit mesaji",            "expect": [r"github|push|commit"]},
    {"id": "r-mcp",          "query": "MCP server fetch_page",                "expect": [r"mcp__|fetch_page|kuroshin[\-_]search"]},
    {"id": "r-paraphrase",   "query": "anladigin uzerinden derin dusunmek",   "expect": [r"derin|reasoning|akıl|akil|düşün|dusun|model"]},
    {"id": "r-mixed",        "query": "PROBE arastirma rapor",                "expect": [r"PROBE|rapor|arastir"]},
]


def hit_at_k(hits, expectations, k):
    blob = "\n".join((h.get("doc") or "") for h in hits[:k]).lower()
    return any(re.search(p.lower(), blob) for p in expectations)


def dense_at_k(rag, q, k):
    cands = rag._dense_search(q, top_k=k)
    return [{"doc": c.document, "id": c.doc_id} for c in cands[:k]]


def main() -> int:
    print(f"[RETRIEVAL ÖLÇÜM @top-{TOP_K}] {datetime.now().isoformat(timespec='seconds')}")
    rag = HybridRAG()
    print(f"Corpus: {rag.corpus_size}, collections: {list(rag._cols.keys())}\n")

    d_pass = h_full_pass = h_norr_pass = 0
    lat_d = lat_h = []
    rows = []
    for tc in TEST_CASES:
        q = tc["query"]
        d = dense_at_k(rag, q, TOP_K)
        hf = rag.search(q, top_m=TOP_K, use_reranker=True)
        hn = rag.search(q, top_m=TOP_K, use_reranker=False)
        d_ok = hit_at_k(d, tc["expect"], TOP_K)
        hf_ok = hit_at_k(hf, tc["expect"], TOP_K)
        hn_ok = hit_at_k(hn, tc["expect"], TOP_K)
        d_pass += d_ok; h_full_pass += hf_ok; h_norr_pass += hn_ok
        if hf: lat_h.append(hf[0].get("_latency_ms", {}).get("total_ms", 0))
        s = lambda b: "✓" if b else "✗"
        print(f"  [{tc['id']}] dense={s(d_ok)} hybrid-full={s(hf_ok)} hybrid-norr={s(hn_ok)} q='{q[:38]}'")
        rows.append({"id": tc["id"], "dense": d_ok, "hybrid_full": hf_ok, "hybrid_norr": hn_ok})

    n = len(TEST_CASES)
    p_d = round(100*d_pass/n, 1); p_hf = round(100*h_full_pass/n, 1); p_hn = round(100*h_norr_pass/n, 1)
    delta = round(p_hf - p_d, 1)
    avg_lat = round(sum(lat_h)/len(lat_h), 1) if lat_h else 0
    print(f"\nprecision@{TOP_K}:  Dense={p_d}%  Hybrid-full={p_hf}%  Hybrid-norerank={p_hn}%")
    print(f"Hybrid-full vs Dense: {delta:+.1f} pp | hybrid avg latency: {avg_lat}ms")

    # En iyi hybrid varyantini sec (kucuk corpus'ta reranker noise yapabilir → norerank kazanir)
    best_hybrid = max(p_hf, p_hn)
    use_rerank = p_hf > p_hn
    integrate = best_hybrid > p_d + INTEGRATION_MARGIN
    if integrate:
        verdict = (f"ENTEGRE ET (use_reranker={use_rerank}): hybrid {best_hybrid}% > dense {p_d}% "
                   f"(+{round(best_hybrid - p_d, 1)}pp)")
    else:
        verdict = f"ENTEGRE ETME: en iyi hybrid {best_hybrid}% dense {p_d}%'i geçmiyor — küçük corpus"
    print(f"\nKARAR: {verdict}")

    rp = REPORTS_DIR / f"retrieval_measure_top{TOP_K}_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps({
        "ts": datetime.now().isoformat(timespec="seconds"), "corpus": rag.corpus_size, "top_k": TOP_K,
        "dense_p": p_d, "hybrid_full_p": p_hf, "hybrid_norr_p": p_hn, "delta_pp": delta,
        "hybrid_avg_latency_ms": avg_lat, "integrate_recommended": integrate, "rows": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
