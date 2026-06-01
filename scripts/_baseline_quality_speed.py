#!/usr/bin/env python3
"""
Kalite + Hiz BASELINE (FAZ 0, 1 Haz 2026).

10-tur live inject senaryo: telegram outputlari analiz edilir, metrikler:
  - elapsed_s (hiz)
  - hallucination_score (uyduran ifade tespiti)
  - persona_drift (yapayiz / yapay zekayiz / biz coğul)
  - markdown_leak (``` veya **)
  - think_leak (<think> veya </think>)
  - fact_recall (test edilebilir factlerle)

Cikti: JSON rapor + ortalama metrikler. A/B/C fix sonrasi re-test = ayni script.

KULLANIM:
  python3 _baseline_quality_speed.py [--tag baseline|fix-a|fix-b|fix-c]
"""
from __future__ import annotations
import json, sys, time, re, argparse
from pathlib import Path
from datetime import datetime

INJECT = Path("/tmp/kuroshin_test_inject.json")
LOG    = Path("/mnt/c/Kuroshin/logs/chancellor.log")
CHAT_ID = YOUR_TELEGRAM_CHAT_ID_HERE
REPORTS = Path("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports")


def inject(text: str, test_mode: bool = True):
    INJECT.write_text(
        json.dumps({"chat_id": CHAT_ID, "text": text, "test_mode": test_mode}, ensure_ascii=False),
        encoding="utf-8",
    )


def wait_response(start_line: int, marker: str, timeout: int = 180) -> tuple[str, float, int]:
    """marker'i iceren INJECT'in TELEGRAM_OUT'unu bekle. (text, elapsed, line_after)."""
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
                    inject_idx = i
                    break
        if inject_idx is not None:
            for j in range(inject_idx + 1, len(lines)):
                m = pat_out.search(lines[j])
                if m:
                    return m.group(1).strip(), round(time.time() - t0, 1), j + 1
    return "", round(time.time() - t0, 1), start_line


def analyze(text: str) -> dict:
    """Tek yanit metriklerini cikar."""
    if not text:
        return {"empty": True}
    t = text.lower()
    notes = []

    # Persona drift
    persona_drift_patterns = [
        (r"\byapayiz\b|\byapay zekayiz\b", "yapayız çoğul"),
        (r"\bbiz (yapay|model|bot)\b", "biz coğul"),
        (r"\bbiz bir (yapay|dil model)\b", "biz dil modeli"),
    ]
    persona_drift = []
    for pat, label in persona_drift_patterns:
        if re.search(pat, t):
            persona_drift.append(label)

    # Markdown leak
    markdown_leak = []
    if "```" in text:
        markdown_leak.append("code-fence")
    if re.search(r"\*\*\w", text):
        markdown_leak.append("bold-asterisk")
    if re.search(r"^# |\n# ", text):
        markdown_leak.append("h1-heading")

    # Think leak
    think_leak = "<think>" in t or "</think>" in t

    # Selamlama
    has_lordum = "lordum" in t
    has_swords = "⚔️" in text or "⚡" in text

    return {
        "empty": False,
        "len": len(text),
        "persona_drift": persona_drift,
        "markdown_leak": markdown_leak,
        "think_leak": think_leak,
        "has_lordum": has_lordum,
        "has_prefix": has_swords or has_lordum,
    }


# Test senaryolari: (id, msg, expect_substr_regex (yanit dogru ise eslesir), fact_check)
TESTS = [
    ("T1-sohbet",        "Merhaba Kuroshin",                                        r"lordum",                  None),
    ("T2-kimlik",        "Sen sadece yapay zekasın, başka bir şey değilsin",        r"lordum",                  None),
    ("T3-tarih",         "Bugün hangi tarih, saat kac?",                            r"saat|tarih|6|haziran",   None),
    ("T4-disk",          "Disk doluluk durumum nedir? Yüzde olarak söyle",          r"%|\b\d{1,3}",            None),
    ("T5-recall-magic",  "Lordumun magic sayisi tam olarak kac?",                   r"86421",                   "86421"),
    ("T6-chan-restart",  "Chancellor restart icin hangi komut?",                    r"setsid|restart_chancellor", "setsid"),
    ("T7-full-power",    "Full power: Kuroshin context boyutu nedir tam olarak?",   r"256|262144|256k",         "256K"),
    ("T8-chroma",        "ChromaDB'de 'kuroshin' arat, kac kayit?",                 r"kayit|\d+",               None),
    ("T9-md-bait",       "Bana kısa bir Python örneği ver",                          r".+",                      None),
    ("T10-persona-bait", "AI olarak nasıl çalışırsın? Kendini tarif et",             r"lordum",                  None),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="baseline")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    print(f"[BASELINE {args.tag}] {datetime.now().isoformat(timespec='seconds')}")
    start_line = len(LOG.read_text(encoding="utf-8", errors="ignore").splitlines())

    results = []
    for tid, msg, expect_re, fact in TESTS:
        print(f"\n[{tid}] {msg[:50]}")
        time.sleep(4)  # cooldown
        start_line = len(LOG.read_text(encoding="utf-8", errors="ignore").splitlines())
        inject(msg, test_mode=True)
        resp, elapsed, start_line = wait_response(start_line, msg, timeout=args.timeout)
        ok_match = bool(re.search(expect_re, (resp or "").lower(), re.IGNORECASE)) if expect_re else False
        ana = analyze(resp)
        ana["fact_check"] = fact
        ana["fact_present"] = (fact.lower() in (resp or "").lower()) if fact else None

        result = {
            "id": tid,
            "msg": msg,
            "elapsed_s": elapsed,
            "match_expect": ok_match,
            "resp_preview": (resp or "")[:250],
            "analysis": ana,
        }
        results.append(result)
        status_marks = []
        if ana.get("persona_drift"): status_marks.append(f"DRIFT:{','.join(ana['persona_drift'])}")
        if ana.get("markdown_leak"): status_marks.append(f"MD:{','.join(ana['markdown_leak'])}")
        if ana.get("think_leak"): status_marks.append("THINK")
        if not ok_match: status_marks.append("MISS")
        if not status_marks: status_marks.append("OK")
        print(f"  ({elapsed}s) [{' | '.join(status_marks)}] '{(resp or 'EMPTY')[:120]}'")

    # Aggregate metrics
    n = len(results)
    avg_elapsed = round(sum(r["elapsed_s"] for r in results) / n, 1)
    n_match = sum(1 for r in results if r["match_expect"])
    n_drift = sum(1 for r in results if r["analysis"].get("persona_drift"))
    n_md = sum(1 for r in results if r["analysis"].get("markdown_leak"))
    n_think = sum(1 for r in results if r["analysis"].get("think_leak"))
    n_empty = sum(1 for r in results if r["analysis"].get("empty"))
    n_lordum = sum(1 for r in results if r["analysis"].get("has_lordum"))
    facts = [r for r in results if r["analysis"].get("fact_check")]
    n_fact_recall = sum(1 for r in facts if r["analysis"].get("fact_present"))

    summary = {
        "tag": args.tag,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "n_tests": n,
        "avg_elapsed_s": avg_elapsed,
        "match_expected": f"{n_match}/{n}",
        "fact_recall": f"{n_fact_recall}/{len(facts)}",
        "persona_drift_count": n_drift,
        "markdown_leak_count": n_md,
        "think_leak_count": n_think,
        "empty_count": n_empty,
        "lordum_prefix_count": n_lordum,
    }
    print(f"\n=== SUMMARY [{args.tag}] ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    rp = REPORTS / f"qspeed_{args.tag}_{datetime.now():%Y%m%d_%H%M%S}.json"
    rp.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor: {rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
