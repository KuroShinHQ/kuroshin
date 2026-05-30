#!/usr/bin/env python3
"""Inspect ChromaDB collections + sample docs (DALGA 5.2 pre-flight)."""
import chromadb

client = chromadb.PersistentClient(path="/root/kuroshin/memory/chroma")
cols = client.list_collections()
print(f"Collection count: {len(cols)}")
for col in cols:
    name = col.name
    cnt = col.count()
    print(f"\n[{name}] {cnt} kayit")
    if cnt > 0:
        sample = col.peek(limit=2)
        for i, d in enumerate(sample.get("documents", [])[:2]):
            print(f"  sample[{i}]: {(d or '')[:100]}")
