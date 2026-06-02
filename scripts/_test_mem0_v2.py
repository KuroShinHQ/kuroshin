#!/usr/bin/env python3
"""YENILIK-3: Mem0 v2.0.4 self_test + kuroshin_episodic karsilastirma."""
import sys, time, os
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")

print("=" * 60)
print("Mem0 v2.x setup + add + search test")
print("=" * 60)

os.environ["OPENAI_API_KEY"] = "kuroshin-secret"
os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:8080/v1"

try:
    import mem0
    print(f"  mem0 version: {getattr(mem0, '__version__', '?')}")
    from mem0 import Memory
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "local",
                "openai_base_url": "http://127.0.0.1:8080/v1",
                "api_key": "kuroshin-secret",
                "temperature": 0.0,
                "max_tokens": 800,
            }
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "mem0_test_v2",
                "path": "/root/kuroshin/memory/chroma",
            }
        },
        "embedder": {
            "provider": "huggingface",
            "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"}
        },
    }
    print(f"  Config: llm=local/llama-server, vector=chroma, embedder=hf")
    t0 = time.time()
    m = Memory.from_config(config)
    print(f"  Memory init: {round((time.time()-t0)*1000,1)}ms")

    # Add 3 fact
    t0 = time.time()
    r1 = m.add("Lord'un favori magic sayisi 86421", user_id="lord")
    add_time = round((time.time()-t0)*1000,1)
    print(f"  add('magic 86421'): {add_time}ms result={str(r1)[:120]}")

    # Search
    t0 = time.time()
    r2 = m.search("Lord'un magic sayisi", user_id="lord", limit=3)
    search_time = round((time.time()-t0)*1000,1)
    print(f"  search('magic sayisi'): {search_time}ms results={len(r2.get('results', []) if isinstance(r2, dict) else r2)}")
    if isinstance(r2, dict):
        for hit in (r2.get('results') or [])[:3]:
            print(f"    - {hit.get('memory', hit)[:80]}")

    print("\n  [MEM0 v2.0.4 SONUC]: setup + add + search BAŞARILI")
except Exception as e:
    print(f"  [MEM0 v2.0.4 SONUC] EXCEPTION: {type(e).__name__}: {str(e)[:300]}")
