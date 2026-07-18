#!/usr/bin/env python3
import json, re

def norm_nums(s):
    nums = re.findall(r'\d+\.?\d*', s.replace(',', '.'))
    return {str(float(n)) if '.' in n else str(int(n)) for n in nums}

def fix_scoring(report_path):
    d = json.load(open(report_path))
    fixed = {"pass": 0, "fail": 0, "total": len(d), "categories": {}}
    for t in d:
        if t.get("type") != "model_test" or t.get("check") != "reasoning":
            fixed["pass" if t["status"] == "PASS" else "fail"] += 1
            continue
        # Recalculate reasoning score
        hint = t.get("answer_hint", "")
        out = t.get("output", "")
        # Extract content from output after "yanit:"
        content = ""
        if "yanit:" in out:
            content = out.split("yanit:", 1)[1]
        hint_nums = norm_nums(hint)
        resp_nums = norm_nums(content)
        score = 0.0
        if hint_nums and resp_nums:
            hits = len(hint_nums & resp_nums)
            score = hits / len(hint_nums)
        passed = score >= 0.5
        if passed:
            fixed["pass"] += 1
        else:
            fixed["fail"] += 1
    return fixed

# Huihui
h = fix_scoring("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_174821.json")
print(f"Huihui 35B: {h['pass']}/{h['total']} PASS ({h['pass']/h['total']*100:.1f}%)")

# Qwen3-Coder 
q = fix_scoring("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_173458.json")
print(f"Qwen3-Coder: {q['pass']}/{q['total']} PASS ({q['pass']/q['total']*100:.1f}%)")

print()
print("=== KATEGORI BAZINDA ===")

def cat_breakdown(report_path, label):
    d = json.load(open(report_path))
    cats = {}
    for t in d:
        cat = t.get("category", "other")
        if cat not in cats:
            cats[cat] = {"pass": 0, "total": 0}
        cats[cat]["total"] += 1
        if t["status"] == "PASS":
            cats[cat]["pass"] += 1
    print(f"\n{label}:")
    for k in sorted(cats.keys()):
        c = cats[k]
        print(f"  {k}: {c['pass']}/{c['total']} ({c['pass']/c['total']*100:.0f}%)")

cat_breakdown("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_173458.json", "Qwen3-Coder 30B")
cat_breakdown("/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_174821.json", "Huihui 35B")
