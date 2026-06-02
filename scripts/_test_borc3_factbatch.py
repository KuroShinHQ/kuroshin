#!/usr/bin/env python3
"""BORC-3 standalone test: idle-loop fact-batch logic dogrulama (gece 02-05 sart bypass)."""
import sys, json, time, datetime
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_episodic import EpisodicMemory

print(f"[BORC-3 TEST] {datetime.datetime.now().isoformat(timespec='seconds')}")

em = EpisodicMemory()
col = em._col
result = col.get(limit=200, include=["documents", "metadatas"])
docs  = result.get("documents", []) or []
metas = result.get("metadatas", []) or []
print(f"  Total episodic records in ChromaDB: {len(docs)}")

cutoff = time.time() - 86400  # son 24h
recent = []
for doc, meta in zip(docs, metas):
    ts_iso = meta.get("ts", "")
    try:
        ts = datetime.datetime.fromisoformat(ts_iso).timestamp()
        if ts >= cutoff and (meta.get("source") or "").lower() != "llm_extract":
            recent.append({"doc": doc, "meta": meta, "ts": ts})
    except Exception:
        continue
print(f"  Recent 24h (non-llm_extract): {len(recent)}")

if not recent:
    print("  YOK kayit — fact-batch atlanır")
    sys.exit(0)

recent.sort(key=lambda x: x["ts"])
conv_text = "\n".join(f"{r['meta'].get('subject','?')}: {r['doc'][:300]}" for r in recent[-30:])
print(f"  conv_text uzunluk: {len(conv_text)} char")
print(f"  Ilk 200 char: {conv_text[:200]}")

t0 = time.time()
facts = em.extract_facts(conv_text, user_id="batch_24h_test")
elapsed = round(time.time() - t0, 1)
print(f"\n[FACT_BATCH] processed={len(recent)} saved={len(facts)} elapsed={elapsed}s")

for f in facts:
    print(f"  - {f.type:11s} | {f.subject[:30]:30s} | {f.text[:80]}")
