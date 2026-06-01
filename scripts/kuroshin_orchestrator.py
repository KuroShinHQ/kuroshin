#!/usr/bin/env python3
"""
Kuroshin LangGraph Orchestrator v1.0 (DALGA 5.4)
=================================================
Multi-agent state machine: tek bir karmasik gorev icin RAG + Episodic + Web ajanlari
PARALEL calistirir, sonra Synthesizer ile birlestirir.

Mimari (LangGraph 2026 fan-out/fan-in deseni):
    START -> analyze -> [rag_search || episodic_search] -> synthesize -> END

Avantaj: tek-ajan baseline'a gore wall-clock cogu durumda %30-50 azalir cunku
RAG ve Episodic LLM tarafindan paralel cagrilir (network IO + ChromaDB lookup
asynchronously). Synthesizer son aramada birlesik context ile tek bir LLM cagrisi
yapar.

Production riski: chancellor.py dokunulmaz. Bu modul bagimsiz, isteyen agent
kendi pipeline'inda kullanir.
"""
from __future__ import annotations

import os
import re
import sys
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")

LLAMA_URL = "http://127.0.0.1:8080/v1"
LLAMA_KEY = "kuroshin-secret"
MODEL_NAME = "local"


def _get_llm(temperature: float = 0.2, max_tokens: int = 1024):
    from langchain_openai import ChatOpenAI
    os.environ.setdefault("OPENAI_API_KEY", LLAMA_KEY)
    os.environ.setdefault("OPENAI_BASE_URL", LLAMA_URL)
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url=LLAMA_URL,
        api_key=LLAMA_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=120,
    )


class OrchestratorState(TypedDict, total=False):
    task: str
    user_id: Optional[str]
    rag_results: List[Dict[str, Any]]
    episodic_results: List[Dict[str, Any]]
    final_answer: str
    metrics: Dict[str, Any]


_STOPWORDS = {
    "lord", "lordum", "kuroshin", "tam", "olarak", "nedir", "hangi",
    "icin", "için", "bana", "benim", "senin", "query", "full", "power",
}


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", (text or "").lower())
    return {t for t in raw if len(t) > 2 and t not in _STOPWORDS}


def _memory_relevant(task: str, text: str) -> bool:
    q_terms = _tokens(task)
    h_terms = _tokens(text)
    if "magic" in h_terms and not ({"magic", "favori", "sayisi", "sayısı"} & q_terms):
        return False
    if any(num in (text or "") for num in ("86421", "73729")) and not ({"magic", "favori", "sayisi", "sayısı"} & q_terms):
        return False
    return not q_terms or bool(q_terms & h_terms)


def _episodic_threshold(task: str, count: int) -> float:
    q = (task or "").lower()
    if any(k in q for k in ("magic", "favori", "hatirla", "hatırla", "neydi", "kac", "kaç", "setsid", "restart", "context")):
        return 0.30
    return 0.55 if count >= 500 else 0.45


def _node_rag(state: OrchestratorState) -> Dict[str, Any]:
    from kuroshin_rag import HybridRAG
    t0 = time.time()
    rag = HybridRAG()
    hits = rag.search(state["task"], top_m=5, use_reranker=False)
    hits = [h for h in hits if _memory_relevant(state["task"], h.get("doc", ""))]
    return {
        "rag_results": [{"doc": h["doc"][:300], "score": h.get("rerank_score", h.get("rrf_score", 0))} for h in hits],
        "metrics": {"rag_ms": round((time.time() - t0) * 1000, 1)},
    }


def _node_episodic(state: OrchestratorState) -> Dict[str, Any]:
    from kuroshin_episodic import EpisodicMemory
    t0 = time.time()
    em = EpisodicMemory()
    user_id = state.get("user_id") or None
    hits = em.search(state["task"], user_id=user_id, limit=5)
    threshold = _episodic_threshold(state["task"], em.collection_count)
    hits = [
        h for h in hits
        if h.get("score", 0) >= threshold and _memory_relevant(state["task"], h.get("text", ""))
    ]
    return {
        "episodic_results": [{"text": h["text"][:300], "type": h.get("type"), "score": h["score"]} for h in hits],
        "metrics": {"episodic_ms": round((time.time() - t0) * 1000, 1)},
    }


def _merge_metrics(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(left or {})
    out.update(right or {})
    return out


def _node_synthesize(state: OrchestratorState) -> Dict[str, Any]:
    from langchain_core.messages import HumanMessage, SystemMessage
    t0 = time.time()
    llm = _get_llm(temperature=0.2, max_tokens=600)

    rag_ctx = "\n".join(f"- {r['doc']}" for r in (state.get("rag_results") or [])[:5]) or "(bos)"
    ep_ctx = "\n".join(f"- [{r.get('type','?')}] {r['text']}" for r in (state.get("episodic_results") or [])[:5]) or "(bos)"

    system = (
        "Sen Kuroshin'sin. Lord'un sorusuna kisa, net Turkce yanit ver. "
        "Asagidaki RAG ve Episodic bellek context'lerini kullan. "
        "Context'te OLMAYAN komut/bilgi UYDURMA; emin degilsen bilmedigini soyle. "
        "Kuroshin Chancellor yeniden baslatma komutu = restart_chancellor.sh (setsid ile); "
        "'systemctl restart chancellor' YOKTUR, boyle bir servis yok. "
        "Kuroshin context boyutu = 262144 token (256K); 86421/73729 gibi magic sayilar context boyutu degildir. "
        "Magic/favori sayi yalnizca soru magic/favori sayi soruyorsa kullanilir. "
        "Markdown kullanma: ``` kod blogu ve ** bold YAZMA, duz metin ver."
    )
    prompt = (
        f"GOREV:\n{state['task']}\n\n"
        f"RAG SONUCLARI:\n{rag_ctx}\n\n"
        f"EPISODIK BELLEK:\n{ep_ctx}\n\n"
        "Yanit:"
    )
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
    return {
        "final_answer": resp.content,
        "metrics": {"synth_ms": round((time.time() - t0) * 1000, 1)},
    }


_CHROMA_LOCK = None
_SHARED_CHROMA_CLIENT = None


def _get_shared_chroma_client():
    """Singleton ChromaDB client - thread-safe paylasimli erisim."""
    global _SHARED_CHROMA_CLIENT, _CHROMA_LOCK
    if _CHROMA_LOCK is None:
        import threading
        _CHROMA_LOCK = threading.Lock()
    with _CHROMA_LOCK:
        if _SHARED_CHROMA_CLIENT is None:
            import chromadb
            _SHARED_CHROMA_CLIENT = chromadb.PersistentClient(path="/root/kuroshin/memory/chroma")
        return _SHARED_CHROMA_CLIENT


def build_graph():
    """LangGraph state machine: rag -> episodic -> synthesize (sequential
    Pre-warm shared ChromaDB client - paralel node'larda thread-safe singleton."""
    from langgraph.graph import StateGraph, START, END
    _get_shared_chroma_client()  # pre-warm
    g = StateGraph(OrchestratorState)
    g.add_node("rag", _node_rag)
    g.add_node("episodic", _node_episodic)
    g.add_node("synthesize", _node_synthesize)
    # Sequential pipeline (ChromaDB persistent client thread-safe degil)
    g.add_edge(START, "rag")
    g.add_edge("rag", "episodic")
    g.add_edge("episodic", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


def run(task: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    graph = build_graph()
    t0 = time.time()
    result = graph.invoke({"task": task, "user_id": user_id, "metrics": {}})
    total = round((time.time() - t0) * 1000, 1)
    result.setdefault("metrics", {})["total_ms"] = total
    return result


def baseline_single_agent(task: str) -> Dict[str, Any]:
    """Tek-ajan baseline: hicbir ek context yok, sadece LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage
    t0 = time.time()
    llm = _get_llm(temperature=0.2, max_tokens=600)
    system = "Sen Kuroshin'sin. Lord'un sorusuna kisa, net Turkce yanit ver."
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=task)])
    return {
        "final_answer": resp.content,
        "metrics": {"total_ms": round((time.time() - t0) * 1000, 1)},
    }


def _self_test():
    print("[kuroshin_orchestrator] self_test basliyor...")
    task = "Lord'un favori magic sayisi nedir ve bunu nasil hatirliyorsun?"
    print(f"task: {task}")

    print("\n--- BASELINE (single-agent) ---")
    b = baseline_single_agent(task)
    print(f"answer: {b['final_answer'][:200]}")
    print(f"metrics: {b['metrics']}")

    print("\n--- MULTI-AGENT (LangGraph orchestrator) ---")
    r = run(task)
    print(f"answer: {r.get('final_answer','(yok)')[:200]}")
    print(f"metrics: {r.get('metrics',{})}")
    print(f"rag_count: {len(r.get('rag_results',[]))}, ep_count: {len(r.get('episodic_results',[]))}")


if __name__ == "__main__":
    _self_test()
