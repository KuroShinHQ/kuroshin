import json
from pathlib import Path

f = Path(r"C:\Kuroshin\scripts\iron_inquisitor\test_suite_full_v2.json")
tests = json.loads(f.read_text(encoding="utf-8"))

timeout_map = {
    "tool_use": 60,
    "web_search": 90,
    "web_fetch": 90,
    "file_ops": 60,
    "service_check": 45,
    "council": 120,
    "path_correctness": 60,
    "hallucination_guard": 60,
    "chroma_fix": 60,
    "model_mgmt": 60,
    "bat_menu": 60,
    "proactive": 60,
    "pdf_fetch": 90,
    "memory": 60,
    "tool_verify": 60,
}

for t in tests:
    tid = t.get("id", "")
    cat = t.get("category", "")
    if "crawlee-sync" in tid:
        t["timeout"] = 240
    elif "crawlee" in tid:
        t["timeout"] = 180
    else:
        t["timeout"] = timeout_map.get(cat, 90)

f.write_text(json.dumps(tests, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(tests)} test timeout ayarlandi:")
for t in tests:
    print(f"  {t['id']}: {t['timeout']}s")
