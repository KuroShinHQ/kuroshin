#!/usr/bin/env python3
"""
Kuroshin Episodic Memory v1.0 (DALGA 5.3)
==========================================
Mem0 OSS yerine Kuroshin'e ozel hafif episodik bellek katmani — llama-server JSON mode
(response_format: json_object) ile fact extraction + ChromaDB persistence.

Bellek tipleri (CoALA / Mem0 doktrin):
  - episodic   : ne oldu (timestamped event, raw)
  - semantic   : ne biliyorum (LLM-extracted fact)
  - procedural : nasil yapilir (workflow pattern)

Avantajlar (Mem0'a karsi):
  - Llama-server JSON mode tam desteklenir (response_format)
  - Tek dosya, harici dependency minimum (chromadb + requests)
  - Mevcut HybridRAG modulu ile uyumlu (ayni ChromaDB altyapisi)

Kullanim:
    from kuroshin_episodic import EpisodicMemory
    em = EpisodicMemory()
    em.record(role="user", content="Lord favori sayisi 73729")
    facts = em.extract_facts("Lord favori sayisi 73729")
    hits = em.search("favori magic sayi", limit=3)
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
CHROMA_PATH = "/root/kuroshin/memory/chroma"
EPISODIC_COL = "kuroshin_episodic"
LOG_PATH = Path("/root/kuroshin/memory/episodic.jsonl")

DEFAULT_USER = "lord"


_FACT_EXTRACTION_PROMPT = """Sen bir hafiza cikaricisin. Konusmayi oku ve KALICI gercekleri cikar: kullanici tercihleri, uzun sureli kararlar, kimlik bilgileri, kurallar, tekrarlayan oruntuler. Her birini etiketle:
  - "semantic"   : kalici gercek ("Lord'un favori sayisi 73729'dur")
  - "episodic"   : zaman damgali olay ("Lord 2026-05-30'da X istedi")
  - "procedural" : nasil-yapilir adimi ("Chancellor restart icin WSL'de setsid kullan")

SADECE ham JSON yanitla, markdown yok, aciklama yok. Gercek yoksa {"facts": []}.

ONEMLI KURAL: "text" ve "subject" alanlari MUTLAKA TURKCE yazilmali. Ingilizce kelime kullanma. Cumleyi Turkce kur.

Sema:
{"facts":[{"type":"semantic","text":"gercegin kendisi (Turkce)","subject":"konu/kategori (Turkce)"}]}

Ornek 1 girdi:
user: Lord'un favori magic sayisi 73729'dur.
assistant: Anladim Lordum.

Ornek 1 cikti:
{"facts":[{"type":"semantic","text":"Lord'un favori magic sayisi 73729'dur","subject":"lord_tercihleri"}]}

Ornek 2 girdi:
user: ne yapiyorsun?
assistant: Lord, dinleniyorum.

Ornek 2 cikti:
{"facts":[]}

Ornek 3 girdi:
user: chancellor'i restart icin hangi komut?
assistant: bash /mnt/c/Kuroshin/scripts/restart_chancellor.sh — setsid ile baslatir.

Ornek 3 cikti:
{"facts":[{"type":"procedural","text":"Chancellor restart icin bash /mnt/c/Kuroshin/scripts/restart_chancellor.sh komutunu calistir; setsid ile baslar","subject":"chancellor_restart"}]}

Simdi bu konusmadan cikar (TURKCE yazmayi unutma):
"""


@dataclass
class MemoryEntry:
    entry_id: str
    user_id: str
    type: str  # episodic | semantic | procedural
    text: str
    subject: str
    ts: str
    source: str  # e.g. conversation:msg_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EpisodicMemory:
    def __init__(
        self,
        chroma_path: str = CHROMA_PATH,
        collection: str = EPISODIC_COL,
        llm_url: str = LLAMA_URL,
        log_path: Optional[Path] = LOG_PATH,
    ):
        import chromadb
        self._client = chromadb.PersistentClient(path=chroma_path)
        self._col = self._client.get_or_create_collection(collection)
        self._llm_url = llm_url
        self._log_path = log_path

    @property
    def collection_count(self) -> int:
        return self._col.count()

    def _append_log(self, entry: Dict[str, Any]) -> None:
        if not self._log_path:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def record_episode(self, role: str, content: str, user_id: str = DEFAULT_USER, source: str = "conv") -> MemoryEntry:
        entry = MemoryEntry(
            entry_id=f"ep_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            type="episodic",
            text=content,
            subject=role,
            ts=_now_iso(),
            source=source,
        )
        meta = {"type": entry.type, "subject": entry.subject, "ts": entry.ts, "source": entry.source, "user_id": user_id}
        self._col.add(documents=[entry.text], ids=[entry.entry_id], metadatas=[meta])
        self._append_log(asdict(entry))
        return entry

    def extract_facts(self, conversation_text: str, user_id: str = DEFAULT_USER) -> List[MemoryEntry]:
        """LLM ile fact extraction (JSON mode)."""
        payload = {
            "model": "local",
            "messages": [{"role": "user", "content": _FACT_EXTRACTION_PROMPT + conversation_text}],
            "max_tokens": 800,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        r = requests.post(self._llm_url, json=payload, timeout=120)
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        out: List[MemoryEntry] = []
        for fact in data.get("facts", []):
            t = (fact.get("type") or "").strip().lower()
            if t not in ("episodic", "semantic", "procedural"):
                continue
            text = (fact.get("text") or "").strip()
            if not text:
                continue
            subject = (fact.get("subject") or "").strip()
            eid = f"{t[:3]}_{uuid.uuid4().hex[:12]}"
            entry = MemoryEntry(
                entry_id=eid,
                user_id=user_id,
                type=t,
                text=text,
                subject=subject,
                ts=_now_iso(),
                source="llm_extract",
            )
            meta = {"type": t, "subject": subject, "ts": entry.ts, "source": "llm_extract", "user_id": user_id}
            self._col.add(documents=[text], ids=[eid], metadatas=[meta])
            self._append_log(asdict(entry))
            out.append(entry)
        return out

    def search(
        self,
        query: str,
        user_id: Optional[str] = DEFAULT_USER,
        types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        where = {}
        if user_id:
            where["user_id"] = user_id
        n_results = min(limit * 3, max(1, self._col.count()))
        if n_results == 0:
            return []
        res = self._col.query(
            query_texts=[query],
            n_results=n_results,
            where=where if where else None,
        )
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        hits = []
        for i in range(len(ids)):
            meta = metas[i] or {}
            if types and meta.get("type") not in types:
                continue
            sim = 1.0 / (1.0 + float(dists[i])) if dists[i] is not None else 0.0
            hits.append({
                "id": ids[i],
                "text": docs[i],
                "type": meta.get("type"),
                "subject": meta.get("subject"),
                "ts": meta.get("ts"),
                "score": round(sim, 4),
            })
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:limit]

    def reset(self, user_id: Optional[str] = None) -> int:
        """Test icin temizle."""
        if user_id:
            res = self._col.get(where={"user_id": user_id})
            ids = res.get("ids", [])
            if ids:
                self._col.delete(ids=ids)
            return len(ids)
        self._client.delete_collection(self._col.name)
        self._col = self._client.get_or_create_collection(EPISODIC_COL)
        return -1


def _self_test():
    print("[kuroshin_episodic] self_test basliyor...")
    em = EpisodicMemory()
    em.reset(user_id="lord_selftest")
    em.record_episode("user", "Lord'un favori magic sayisi 73729'dur.", user_id="lord_selftest")
    em.record_episode("assistant", "Anladim Lordum, favori sayiniz kayitli: 73729.", user_id="lord_selftest")

    facts = em.extract_facts(
        "user: Lord'un favori magic sayisi 73729'dur.\nassistant: Anladim Lordum, kayitli: 73729.",
        user_id="lord_selftest"
    )
    print(f"Extracted facts: {len(facts)}")
    for f in facts:
        print(f"  [{f.type}] subject='{f.subject}' text='{f.text[:80]}'")

    hits = em.search("favori magic sayi", user_id="lord_selftest", limit=3)
    print(f"Search hits: {len(hits)}")
    for h in hits:
        print(f"  score={h['score']} type={h['type']} text='{(h['text'] or '')[:80]}'")


if __name__ == "__main__":
    _self_test()
