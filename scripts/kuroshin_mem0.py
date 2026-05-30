#!/usr/bin/env python3
"""
Kuroshin Mem0 Episodik Bellek v1.0 (DALGA 5.3)
================================================
Mem0 (LoCoMo 92.5 lider, p95 -%91, token -%90 vs naive context) ile
Kuroshin'e uzun-vadeli episodik + semantic + procedural bellek katmani.

Local-only:
  - LLM: llama-server (Huihui-Qwen3.6-35B-A3B) @ 127.0.0.1:8080 (OpenAI-compatible)
  - Embedder: HuggingFace all-MiniLM-L6-v2 (lokal, ~80MB)
  - Vector store: ChromaDB (`/root/kuroshin/memory/chroma_mem0` — ayri koleksiyon)

Bellek tipleri:
  - Episodic: ne oldu, ne zaman, kimle (timestamped events)
  - Semantic: ne biliyorum (extracted facts)
  - Procedural: nasil yapilir (workflow patterns)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1"
LLAMA_MODEL_NAME = "local"
LLAMA_API_KEY = "kuroshin-secret"
CHROMA_PATH = "/root/kuroshin/memory/chroma_mem0"
COLLECTION = "mem0_kuroshin"
EMBED_MODEL = "all-MiniLM-L6-v2"


def build_config() -> Dict[str, Any]:
    return {
        "llm": {
            "provider": "openai",
            "config": {
                "model": LLAMA_MODEL_NAME,
                "openai_base_url": LLAMA_SERVER_URL,
                "api_key": LLAMA_API_KEY,
                "temperature": 0.0,
                "max_tokens": 1500,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": EMBED_MODEL,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": COLLECTION,
                "path": CHROMA_PATH,
            },
        },
    }


def get_memory():
    os.environ.setdefault("OPENAI_API_KEY", LLAMA_API_KEY)
    os.environ.setdefault("OPENAI_BASE_URL", LLAMA_SERVER_URL)
    from mem0 import Memory
    return Memory.from_config(build_config())


def add_event(memory, content: str, user_id: str = "lord") -> Dict[str, Any]:
    return memory.add(content, user_id=user_id)


def add_conversation(memory, messages: List[Dict[str, str]], user_id: str = "lord") -> Dict[str, Any]:
    return memory.add(messages, user_id=user_id)


def search_memory(memory, query: str, user_id: str = "lord", limit: int = 5) -> List[Dict[str, Any]]:
    return memory.search(query=query, user_id=user_id, limit=limit)


def list_all(memory, user_id: str = "lord") -> List[Dict[str, Any]]:
    return memory.get_all(user_id=user_id)


def _self_test():
    print("[kuroshin_mem0] self_test basliyor...")
    mem = get_memory()
    print(f"Memory hazirlandi.")
    sample_msgs = [
        {"role": "user", "content": "Lord'un favori magic sayisi 73729'dur."},
        {"role": "assistant", "content": "Anladim Lordum, favori sayiniz 73729 olarak kaydedildi."},
    ]
    res = add_conversation(mem, sample_msgs)
    print(f"add result: {res}")
    hits = search_memory(mem, "favori magic sayi nedir", limit=3)
    print(f"search result count: {len(hits) if hits else 0}")
    for h in (hits or [])[:3]:
        if isinstance(h, dict):
            print(f"  memory={h.get('memory','?')[:120]} score={h.get('score','?')}")


if __name__ == "__main__":
    _self_test()
