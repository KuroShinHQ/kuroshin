#!/usr/bin/env python3
"""Episodic store envanteri — entegrasyon değer/erken-mi kararı için."""
import sys
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_episodic import EpisodicMemory

em = EpisodicMemory()
total = em._col.count()
print(f"kuroshin_episodic count: {total}")

# Tum kayitlar (user filtresiz) — tip dagilimi
try:
    allr = em._col.get(include=["metadatas"])
    metas = allr.get("metadatas", []) or []
    types = {}
    users = {}
    for m in metas:
        m = m or {}
        types[m.get("type", "?")] = types.get(m.get("type", "?"), 0) + 1
        users[m.get("user_id", "?")] = users.get(m.get("user_id", "?"), 0) + 1
    print("type dagilimi:", types)
    print("user_id dagilimi:", users)
except Exception as e:
    print("meta okuma hatasi:", e)

# Ornek aramalar (user filtresiz — hepsini gor)
for q in ["github push commit", "favori magic sayi", "ruya gece karanlik", "kuroshin kimlik sansolye", "arastirma rapor"]:
    hits = em.search(q, user_id=None, limit=3)
    print(f"\nQ='{q}': {len(hits)} hit")
    for h in hits:
        print(f"  [{h.get('type')}] score={h.get('score')} ts={h.get('ts')} subj={h.get('subject')}: {(h.get('text') or '')[:90]}")
