"""
mcp_toggle.py — Kuroshin MCP'lerini .claude.json'da aktif/devre dışı bırakır.
Kullanım: python mcp_toggle.py true   (aktif - mcpServers'a geri ekler)
           python mcp_toggle.py false  (devre dışı - mcpServers'dan kaldırır, backup'a saklar)

NOT: disabled:true alanı Claude Code tarafından dikkate alınmıyor.
     Gerçek devre dışı bırakma için girişleri mcpServers'dan tamamen kaldırıyoruz.
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

BACKUP_KEY = "mcpServersKuroshinBackup"

enabled = True
if len(sys.argv) > 1:
    enabled = sys.argv[1].strip().lower() not in ("false", "0", "off", "devre")

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
backup = data.get(BACKUP_KEY, {})
changed = 0

if enabled:
    # Backup'tan mcpServers'a geri yükle
    for mcp_name in KUROSHIN_MCPS:
        if mcp_name in backup:
            servers[mcp_name] = backup.pop(mcp_name)
            changed += 1
        elif mcp_name in servers:
            # Zaten aktif, disabled flag'i temizle
            servers[mcp_name].pop("disabled", None)
            changed += 1
else:
    # mcpServers'dan kaldır, backup'a sakla
    for mcp_name in KUROSHIN_MCPS:
        if mcp_name in servers:
            backup[mcp_name] = servers.pop(mcp_name)
            changed += 1

data["mcpServers"] = servers
data[BACKUP_KEY] = backup

with open(claude_json, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

state = "AKTIF" if enabled else "DEVRE DISI"
print(f"MCP toggle OK: {changed} sunucu {state} ({', '.join(KUROSHIN_MCPS)})")
