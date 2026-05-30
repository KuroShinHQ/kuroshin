#!/usr/bin/env python3
"""
Kuroshin Hybrid RAG v1.0 (DALGA 5.2)
=====================================
Mimari: Dense (ChromaDB) + Sparse (BM25) -> RRF birlestirme -> Cross-encoder rerank (BGE @9003).

Production 2026 deseni (Cohere, OpenAI RAG cookbook standardi):
  Dense top-K_d + BM25 top-K_s -> RRF k=60 -> top-N candidates -> reranker -> top-M.

Kullanim:
    from kuroshin_rag import HybridRAG
    rag = HybridRAG()
    hits = rag.search("Lord favori sayisi", top_m=5)
    for h in hits:
        print(h["score"], h["doc"][:120])
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

import requests

CHROMA_PATH = "/root/kuroshin/memory/chroma"
RERANKER_URL = "http://127.0.0.1:9003/rerank"
DEFAULT_RRF_K = 60


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", text.lower())
    return tokens


@dataclass
class Candidate:
    doc_id: str
    document: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0


class HybridRAG:
    """Dense + BM25 + RRF + Cross-encoder rerank pipeline."""

    def __init__(self, collections: Optional[List[str]] = None, chroma_path: str = CHROMA_PATH):
        import chromadb
        from rank_bm25 import BM25Okapi

        self._client = chromadb.PersistentClient(path=chroma_path)
        all_cols = {c.name: c for c in self._client.list_collections()}
        if collections is None:
            collections = list(all_cols.keys())
        self._cols = {n: all_cols[n] for n in collections if n in all_cols}

        self._corpus: List[Tuple[str, str, Dict[str, Any], str]] = []
        for name, col in self._cols.items():
            cnt = col.count()
            if cnt == 0:
                continue
            data = col.get(include=["documents", "metadatas"])
            ids = data.get("ids") or []
            docs = data.get("documents") or []
            metas = data.get("metadatas") or [{} for _ in ids]
            for i in range(len(ids)):
                self._corpus.append((f"{name}::{ids[i]}", docs[i] or "", metas[i] or {}, name))

        tokenized = [_tokenize(doc) for (_, doc, _, _) in self._corpus]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None
        self._BM25Okapi = BM25Okapi
        self._tokenized_corpus = tokenized

    @property
    def corpus_size(self) -> int:
        return len(self._corpus)

    def _dense_search(self, query: str, top_k: int = 50) -> List[Candidate]:
        out: List[Candidate] = []
        for name, col in self._cols.items():
            try:
                res = col.query(query_texts=[query], n_results=min(top_k, max(1, col.count())))
            except Exception:
                continue
            ids = (res.get("ids") or [[]])[0]
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]
            for rank, (raw_id, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists)):
                cid = f"{name}::{raw_id}"
                sim = 1.0 / (1.0 + float(dist)) if dist is not None else 0.0
                out.append(Candidate(
                    doc_id=cid,
                    document=doc or "",
                    metadata=meta or {},
                    dense_rank=rank,
                    dense_score=sim,
                ))
        out.sort(key=lambda c: c.dense_score, reverse=True)
        return out[:top_k]

    def _sparse_search(self, query: str, top_k: int = 50) -> List[Candidate]:
        if not self._bm25 or not self._corpus:
            return []
        q_tok = _tokenize(query)
        scores = self._bm25.get_scores(q_tok)
        idx_sorted = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        out: List[Candidate] = []
        for rank, idx in enumerate(idx_sorted[:top_k]):
            cid, doc, meta, _ = self._corpus[idx]
            out.append(Candidate(
                doc_id=cid,
                document=doc,
                metadata=meta,
                sparse_rank=rank,
                sparse_score=float(scores[idx]),
            ))
        return out

    @staticmethod
    def _rrf_fuse(dense: List[Candidate], sparse: List[Candidate], k: int = DEFAULT_RRF_K) -> List[Candidate]:
        merged: Dict[str, Candidate] = {}
        for cand in dense:
            merged[cand.doc_id] = cand
        for cand in sparse:
            existing = merged.get(cand.doc_id)
            if existing is None:
                merged[cand.doc_id] = cand
            else:
                existing.sparse_rank = cand.sparse_rank
                existing.sparse_score = cand.sparse_score
        for cid, cand in merged.items():
            score = 0.0
            if cand.dense_rank is not None:
                score += 1.0 / (k + cand.dense_rank + 1)
            if cand.sparse_rank is not None:
                score += 1.0 / (k + cand.sparse_rank + 1)
            cand.rrf_score = score
        fused = list(merged.values())
        fused.sort(key=lambda c: c.rrf_score, reverse=True)
        return fused

    def _cross_encoder_rerank(self, query: str, candidates: List[Candidate], top_m: int = 10) -> List[Candidate]:
        if not candidates:
            return []
        docs = [c.document for c in candidates]
        try:
            r = requests.post(
                RERANKER_URL,
                json={"query": query, "documents": docs, "top_n": min(top_m, len(docs))},
                timeout=30,
            )
            r.raise_for_status()
            ranked = r.json().get("ranked", [])
            for item in ranked:
                idx = item.get("index", -1)
                if 0 <= idx < len(candidates):
                    candidates[idx].rerank_score = float(item.get("score", 0.0))
            ordered = sorted(candidates, key=lambda c: c.rerank_score, reverse=True)
            return ordered[:top_m]
        except Exception:
            return candidates[:top_m]

    def search(
        self,
        query: str,
        top_k_dense: int = 50,
        top_k_sparse: int = 50,
        rerank_top_n: int = 50,
        top_m: int = 10,
        use_reranker: bool = True,
    ) -> List[Dict[str, Any]]:
        t0 = time.time()
        dense = self._dense_search(query, top_k=top_k_dense)
        t_dense = time.time()
        sparse = self._sparse_search(query, top_k=top_k_sparse)
        t_sparse = time.time()
        fused = self._rrf_fuse(dense, sparse)
        t_rrf = time.time()
        candidates = fused[:rerank_top_n]
        if use_reranker:
            final = self._cross_encoder_rerank(query, candidates, top_m=top_m)
        else:
            final = candidates[:top_m]
        t_rerank = time.time()

        latency = {
            "dense_ms": round((t_dense - t0) * 1000, 1),
            "sparse_ms": round((t_sparse - t_dense) * 1000, 1),
            "rrf_ms": round((t_rrf - t_sparse) * 1000, 1),
            "rerank_ms": round((t_rerank - t_rrf) * 1000, 1),
            "total_ms": round((t_rerank - t0) * 1000, 1),
        }

        out = []
        for c in final:
            out.append({
                "id": c.doc_id,
                "doc": c.document,
                "metadata": c.metadata,
                "dense_score": round(c.dense_score, 4),
                "sparse_score": round(c.sparse_score, 4),
                "rrf_score": round(c.rrf_score, 6),
                "rerank_score": round(c.rerank_score, 4),
                "_latency_ms": latency,
            })
        return out


def _self_test():
    print("[kuroshin_rag] self_test basliyor...")
    rag = HybridRAG()
    print(f"corpus={rag.corpus_size} collections={list(rag._cols.keys())}")
    if rag.corpus_size == 0:
        print("[WARN] ChromaDB bos, anlamli test yapilamiyor")
        return
    sample_query = "Kuroshin"
    hits = rag.search(sample_query, top_m=3)
    for h in hits:
        print(f"  rerank={h['rerank_score']:.4f} rrf={h['rrf_score']:.6f} doc='{(h['doc'] or '')[:80]}'")
    print(f"latency: {hits[0]['_latency_ms'] if hits else 'n/a'}")


if __name__ == "__main__":
    _self_test()
