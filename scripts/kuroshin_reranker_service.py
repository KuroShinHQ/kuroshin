#!/usr/bin/env python3
"""
Kuroshin BGE-Reranker Servisi v1.0
Port 9003 — ChromaDB sonuçlarını sıralar, en iyi N'i döndürür.
"""
import time
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

SERVICE_PORT = 9003
MODEL_NAME = "BAAI/bge-reranker-v2-m3"

reranker = None


def load_reranker():
    global reranker
    try:
        from FlagEmbedding import FlagReranker
        reranker = FlagReranker(MODEL_NAME, use_fp16=True, device="cuda")
        print(f"[RERANKER] BGE-Reranker-v2-M3 yüklendi (CUDA fp16)", flush=True)
    except Exception as e:
        print(f"[RERANKER WARN] CUDA başarısız, CPU deneniyor: {e}", flush=True)
        try:
            from FlagEmbedding import FlagReranker
            reranker = FlagReranker(MODEL_NAME, use_fp16=False, device="cpu")
            print(f"[RERANKER] BGE-Reranker-v2-M3 yüklendi (CPU)", flush=True)
        except Exception as e2:
            print(f"[RERANKER ERROR] Yüklenemedi: {e2}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_reranker()
    print(f"[RERANKER] Servis hazır — Port {SERVICE_PORT}", flush=True)
    yield


app = FastAPI(lifespan=lifespan)


class RerankRequest(BaseModel):
    query: str
    documents: List[str]
    top_n: int = 3


class RerankResponse(BaseModel):
    ranked: List[dict]
    elapsed: float


@app.get("/health")
def health():
    return {"status": "ready", "model": MODEL_NAME, "loaded": reranker is not None}


@app.post("/rerank")
def rerank(req: RerankRequest) -> RerankResponse:
    t0 = time.time()
    if reranker is None:
        return RerankResponse(ranked=[], elapsed=0.0)

    pairs = [(req.query, doc) for doc in req.documents]
    scores = reranker.compute_score(pairs)

    ranked = sorted(
        [{"document": doc, "score": float(score), "index": i}
         for i, (doc, score) in enumerate(zip(req.documents, scores))],
        key=lambda x: x["score"],
        reverse=True
    )

    return RerankResponse(
        ranked=ranked[:req.top_n],
        elapsed=round(time.time() - t0, 3)
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=SERVICE_PORT, log_level="warning")
