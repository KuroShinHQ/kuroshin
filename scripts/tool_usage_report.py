#!/usr/bin/env python3
"""E-11 (29 May 2026): Tool kullanım histogramı.

chancellor.log + autonomous.log dosyalarını parse eder, son N gün için tool çağrı
istatistiklerini çıkarır. "Zombi" tool (hiç çağrılmayan) tespiti yapar.

Kullanım:
    python3 scripts/tool_usage_report.py            # son 7 gün
    python3 scripts/tool_usage_report.py --days 30  # özel pencere
    python3 scripts/tool_usage_report.py --json     # makine okuyabilir çıktı
"""
import re, json, sys, argparse
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta

LOG_FILES = [
    Path("/mnt/c/Kuroshin/logs/chancellor.log"),
    Path("/mnt/c/Kuroshin/logs/chancellor.log.1"),
    Path("/mnt/c/Kuroshin/logs/chancellor.log.2"),
    Path("/mnt/c/Kuroshin/logs/chancellor.log.3"),
    Path("/mnt/c/Kuroshin/logs/autonomous.log"),
]

# Bilinen tüm araçlar (chancellor.py TOOLS listesi ile uyumlu — ARCHITECTURE.md)
KNOWN_TOOLS = {
    "walker_research", "web_search", "system_command", "memory_query",
    "write_file", "read_file", "open_url", "youtube_play",
    "model_switch", "pdf_reader", "memory_manage", "chroma_search",
    "memory_integrity_scan", "self_update", "reminder", "internet_status",
    "system_info", "reddit_read", "reddit_tool", "github", "gemini",
    "aktivite_gunluk", "goal_manage", "task_status",
}

# Log içindeki tool çağrı pattern'leri
RE_TOOL_CALL = re.compile(r'\[(?:RUN_TOOL|TOOL_CALL|EXPLICIT|CHANCELLOR)\][^\n]*?\b(' +
                          "|".join(re.escape(t) for t in KNOWN_TOOLS) +
                          r')\b', re.IGNORECASE)
RE_TIMESTAMP = re.compile(r'(\d{4}-\d{2}-\d{2})')


def parse_logs(days: int) -> dict:
    """Son N gün için tool çağrı counter + timeline çıkar."""
    cutoff = (datetime.now() - timedelta(days=days)).date()
    counter: Counter = Counter()
    daily: dict = {}      # {date: Counter}
    total_lines = 0
    for f in LOG_FILES:
        if not f.exists():
            continue
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    total_lines += 1
                    m_ts = RE_TIMESTAMP.search(line)
                    if not m_ts:
                        continue
                    try:
                        d = datetime.strptime(m_ts.group(1), "%Y-%m-%d").date()
                    except ValueError:
                        continue
                    if d < cutoff:
                        continue
                    m_tool = RE_TOOL_CALL.search(line)
                    if m_tool:
                        tool = m_tool.group(1).lower()
                        counter[tool] += 1
                        daily.setdefault(str(d), Counter())[tool] += 1
        except Exception as e:
            print(f"[WARN] {f.name}: {e}", file=sys.stderr)
    return {
        "counter": counter,
        "daily": {d: dict(c) for d, c in daily.items()},
        "total_lines": total_lines,
        "window_days": days,
        "cutoff": str(cutoff),
    }


def find_zombies(counter: Counter) -> list:
    """Hiç çağrılmamış tool'lar."""
    return sorted(KNOWN_TOOLS - set(counter.keys()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    data = parse_logs(args.days)
    counter = data["counter"]
    zombies = find_zombies(counter)
    total_calls = sum(counter.values())

    if args.json:
        print(json.dumps({
            "window_days": args.days,
            "total_calls": total_calls,
            "histogram": dict(counter.most_common()),
            "zombies": zombies,
            "log_lines_scanned": data["total_lines"],
        }, ensure_ascii=False, indent=2))
        return

    print(f"╔═══════════════════════════════════════════════════════╗")
    print(f"║  E-11 Tool Usage Report — son {args.days} gün")
    print(f"║  Toplam çağrı: {total_calls} | Tanınan tool: {len(KNOWN_TOOLS)}")
    print(f"║  Tarama: {data['total_lines']} satır, {data['cutoff']}+")
    print(f"╚═══════════════════════════════════════════════════════╝")
    print()
    if not counter:
        print("(Hiç tool çağrısı bulunamadı — log boş veya servis çalışmamış)")
        return
    width = max((len(t) for t in counter), default=10)
    for tool, n in counter.most_common():
        bar = "█" * min(int(n / max(counter.values()) * 40), 40)
        print(f"  {tool:<{width}}  {n:>4}  {bar}")
    print()
    if zombies:
        print(f"🧟 Zombi araçlar ({len(zombies)} tane — son {args.days} gün hiç çağrılmadı):")
        for t in zombies:
            print(f"  - {t}")
    else:
        print("✅ Zombi araç yok — tüm araçlar son pencerede en az 1 kez kullanıldı.")


if __name__ == "__main__":
    main()
