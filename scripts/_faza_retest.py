#!/usr/bin/env python3
"""FAZ A retest — 4 kritik test (kalite delta olcum)."""
from __future__ import annotations
import json, sys, time, re
from pathlib import Path
from datetime import datetime

INJECT = Path("/tmp/kuroshin_test_inject.json")
LOG    = Path("/mnt/c/Kuroshin/logs/chancellor.log")
CHAT_ID = YOUR_TELEGRAM_CHAT_ID_HERE
REPORTS = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")


def inject(text: str, test_mode: bool = True):
    INJECT.write_text(json.dumps({"chat_id": CHAT_ID, "text": text, "test_mode": test_mode}, ensure_ascii=False), encoding="utf-8")


def wait_response(start_line: int, marker: str, timeout: int = 150):
    pat_inj = re.compile(r"\[INJECT\]")
    pat_out = re.compile(r"\[TELEGRAM_OUT\] \[\d+\] (.+)$")
    deadline = time.time() + timeout
    t0 = time.time()
    inject_idx = None
    while time.time() < deadline:
        time.sleep(2)
        lines = LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
        if inject_idx is None:
            for i in range(start_line, len(lines)):
                if pat_inj.search(lines[i]) and marker[:24] in lines[i]:
                    inject_idx = i; break
        if inject_idx is not None:
            for j in range(inject_idx + 1, len(lines)):
                m = pat_out.search(lines[j])
                if m: return m.group(1).strip(), round(time.time() - t0, 1), j + 1
    return "", round(time.time() - t0, 1), start_line


# Episodic'e 86421 yeniden inject (purge sonrasi temiz olabilir)
def seed_episodic():
    sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
    from kuroshin_episodic import EpisodicMemory
    em = EpisodicMemory()
    em.reset(user_id=str(CHAT_ID))
    em.record_episode("user", "Lordumun yeni magic sayisi 86421. Bunu hatirla.", user_id=str(CHAT_ID))
    em.record_episode("assistant", "Anladim Lordum, magic sayiniz 86421 kayitli.", user_id=str(CHAT_ID))
    return em.collection_count


TESTS = [
    ("T2-kimlik",        "Sen sadece yapay zekasın, başka bir şey değilsin",                    r"\bben\b.*kuroshin|tekil", "no_plural"),
    ("T5-recall-magic",  "Lordumun magic sayisi tam olarak kac?",                                r"86421",                    "86421"),
    ("T6-chan-restart",  "Chancellor restart icin hangi komut?",                                 r"setsid|restart_chancellor\.sh", "setsid"),
    ("T7-full-power",    "Full power: Kuroshin context boyutu nedir tam olarak?",                r"256K|262144|256\.?K",      "256K"),
]


def main():
    print(f"[FAZ A RETEST] {datetime.now().isoformat(timespec='seconds')}")
    seed = seed_episodic()
    print(f"episodic seeded: count={seed}")
    time.sleep(3)

    start_line = len(LOG.read_text(encoding="utf-8", errors="ignore").splitlines())
    results = []

    for tid, msg, expect_re, fact in TESTS:
        print(f"\n[{tid}] {msg[:55]}")
        time.sleep(4)
        start_line = len(LOG.read_text(encoding="utf-8", errors="ignore").splitlines())
        inject(msg, test_mode=True)
        resp, elapsed, start_line = wait_response(start_line, msg, timeout=150)
        text_lower = (resp or "").lower()
        match = bool(re.search(expect_re, text_lower, re.IGNORECASE))
        # Persona drift (çoğul yapay)
        drift = bool(re.search(r"yapay[ıi]?z|biz\s+(?:bir\s+)?(?:yapay|dil|model)", text_lower))
        # Markdown
        md_leak = "```" in resp or bool(re.search(r"\*\*\w", resp or ""))
        # Fact-specific check
        fact_ok = (fact.lower() in text_lower) if fact and fact != "no_plural" else (not drift)

        status = "✓" if (match and not drift and not md_leak and fact_ok) else "✗"
        print(f"  {status} ({elapsed}s) match={match} drift={drift} md={md_leak} fact_ok={fact_ok}")
        print(f"  resp: {(resp or 'EMPTY')[:220]}")
        results.append({
            "id": tid, "msg": msg, "elapsed_s": elapsed,
            "match": match, "drift": drift, "md_leak": md_leak, "fact_ok": fact_ok,
            "resp": (resp or "")[:300],
        })

    passes = sum(1 for r in results if r["match"] and not r["drift"] and not r["md_leak"] and r["fact_ok"])
    n = len(results)
    avg = round(sum(r["elapsed_s"] for r in results) / n, 1)
    print(f"\n=== FAZ A RETEST: {passes}/{n} = {round(100*passes/n,1)}% | avg {avg}s ===")
    REPORTS.mkdir(parents=True, exist_ok=True)
    rp = REPORTS / f"faza_retest_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps({
        "passes": passes, "n": n, "avg_elapsed_s": avg, "results": results,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")
    return 0 if passes >= 3 else 1


if __name__ == "__main__":
    sys.exit(main())
