#!/usr/bin/env python3
import json

comparison = {
    "Qwen3-Coder 30B": "/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_173844.json",
    "Huihui 35B": "/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_174821.json",
}

for name, path in comparison.items():
    d = json.load(open(path))
    cats = {}
    for t in d:
        cat = t.get("category", "other")
        if cat not in cats:
            cats[cat] = {"pass": 0, "total": 0}
        cats[cat]["total"] += 1
        if t["status"] == "PASS":
            cats[cat]["pass"] += 1

    total_pass = sum(c["pass"] for c in cats.values())
    total = sum(c["total"] for c in cats.values())
    print(f"\n=== {name} ===")
    print(f"  TOPLAM: {total_pass}/{total} ({total_pass/total*100:.1f}%)")
    for k in sorted(cats.keys()):
        c = cats[k]
        p = c["pass"]
        t = c["total"]
        bar = "+" * p + "-" * (t - p)
        print(f"  {k}: [{bar}] ({p}/{t})")
