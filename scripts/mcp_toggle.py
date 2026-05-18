"""
mcp_toggle.py — Kuroshin MCP'lerini .claude.json'da aktif/devre dışı bırakır.
Kullanım: python mcp_toggle.py true   (aktif)
           python mcp_toggle.py false  (devre dışı)
PS 5.1 uyumlu: && zinciri yok, json.dump ensure_ascii=True (BOM yok).
"""
import json
import os
import sys

KUROSHIN_MCPS = [
    "kuroshin-echo",
    "kuroshin-search",
    "kuroshin-bridge",
    "kuroshin-walker",
    "kuroshin-council",
    "kuroshin-deerflow",
]

enabled = True
if len(sys.argv) > 1:
    enabled = sys.argv[1].strip().lower() not in ("false", "0", "off", "devre")

# .claude.json Windows home dizininde
claude_json = os.path.join(os.path.expanduser("~"), ".claude.json")

try:
    with open(claude_json, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"HATA: {claude_json} bulunamadi")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"HATA: JSON parse hatasi: {e}")
    sys.exit(1)

servers = data.get("mcpServers", {})
changed = 0
for mcp_name in KUROSHIN_MCPS:
    if mcp_name in servers:
        servers[mcp_name]["disabled"] = not enabled
        changed += 1

data["mcpServers"] = servers

with open(claude_json, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

state = "AKTIF" if enabled else "DEVRE DISI"
print(f"MCP toggle OK: {changed} sunucu {state} ({', '.join(KUROSHIN_MCPS)})")
