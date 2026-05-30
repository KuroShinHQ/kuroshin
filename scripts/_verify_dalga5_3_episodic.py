#!/usr/bin/env python3
"""
DALGA 5.3 Verify — Episodic Memory cross-session retrieval testi.

5 oturum simule et, her oturumda farkli olay/tercih kaydet.
6. oturumda sorgu yap, dogru fact'i getiriyor mu?
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_episodic import EpisodicMemory

REPORTS_DIR = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TEST_USER = "lord_verify_d5_3"


# 5 oturumluk dogal konusma — her birinde farkli bilgi
SESSIONS = [
    {
        "id": "s1",
        "messages": [
            ("user", "Lord'un favori magic sayisi 73729'dur."),
            ("assistant", "Anladim Lordum, 73729 kayitli."),
        ],
    },
    {
        "id": "s2",
        "messages": [
            ("user", "Kahveyi sutsuz iceriyorum."),
            ("assistant", "Sutsuz kahve tercihi not edildi."),
        ],
    },
    {
        "id": "s3",
        "messages": [
            ("user", "Chancellor'i setsid ile baslat — nohup yetmiyor WSL'de."),
            ("assistant", "Setsid ile baslatma proseduru hatirimda."),
        ],
    },
    {
        "id": "s4",
        "messages": [
            ("user", "2026-05-30'da Dalga 5.1 ile context 256K'ya cikti."),
            ("assistant", "Tarihli kayit: 256K ctx 30 Mayis'ta aktif edildi."),
        ],
    },
    {
        "id": "s5",
        "messages": [
            ("user", "Manuel test sevmiyorum — sistem kendi test etsin."),
            ("assistant", "Manuel test yasagi anladim, hep otomatize edecegim."),
        ],
    },
]

# 6. oturumdaki sorgular + beklenen fact pattern
QUERIES = [
    {"id": "q1-magic", "query": "favori sayi nedir",                  "expect": r"73729"},
    {"id": "q2-coffee", "query": "kahve nasil iciyorum",              "expect": r"suts[uü]z|sut.?suz|sütsüz"},
    {"id": "q3-chancellor", "query": "chancellor restart prosedur",   "expect": r"setsid"},
    {"id": "q4-context", "query": "ne zaman context buyutuldu",       "expect": r"256K|262144|30.?Mayis|256.?K"},
    {"id": "q5-rule", "query": "Lord'un manuel test kurali",          "expect": r"manuel|automate|otomati"},
]


def main() -> int:
    print(f"[DALGA 5.3 VERIFY] {datetime.now().isoformat(timespec='seconds')}")
    em = EpisodicMemory()
    em.reset(user_id=TEST_USER)
    print(f"Reset done, starting empty.")

    # 5 oturumu kaydet
    for sess in SESSIONS:
        for role, content in sess["messages"]:
            em.record_episode(role, content, user_id=TEST_USER, source=sess["id"])
        # Her oturumdan fact cikar
        conv_text = "\n".join(f"{r}: {c}" for r, c in sess["messages"])
        try:
            facts = em.extract_facts(conv_text, user_id=TEST_USER)
            print(f"  [{sess['id']}] facts extracted: {len(facts)}")
        except Exception as e:
            print(f"  [{sess['id']}] fact extraction FAIL: {e}")

    print(f"\nCollection count after 5 sessions: {em.collection_count}")

    # 6. oturum: cross-session retrieval
    import re
    passes = 0
    results = []
    for q in QUERIES:
        hits = em.search(q["query"], user_id=TEST_USER, limit=5)
        text_blob = "\n".join((h.get("text") or "") for h in hits)
        match = bool(re.search(q["expect"], text_blob, re.IGNORECASE))
        if match:
            passes += 1
        status = "✓" if match else "✗"
        top = (hits[0]["text"][:80] if hits else "EMPTY")
        print(f"  [{q['id']}] {status} q='{q['query']}' -> top='{top}' (n={len(hits)})")
        results.append({
            "id": q["id"],
            "query": q["query"],
            "expect_regex": q["expect"],
            "pass": match,
            "n_hits": len(hits),
            "top_text": hits[0]["text"][:120] if hits else None,
            "top_score": hits[0]["score"] if hits else 0.0,
            "top_type": hits[0]["type"] if hits else None,
        })

    n = len(QUERIES)
    pct = round(100 * passes / n, 1)
    print(f"\nCross-session retrieval: {passes}/{n} = {pct}%")
    overall_pass = pct >= 80.0
    print(f"VERIFY: {'PASS' if overall_pass else 'FAIL'}")

    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "test_user": TEST_USER,
        "n_sessions": len(SESSIONS),
        "collection_count": em.collection_count,
        "score_pct": pct,
        "overall_pass": overall_pass,
        "results": results,
    }
    rp = REPORTS_DIR / f"dalga5_3_episodic_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")

    em.reset(user_id=TEST_USER)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
