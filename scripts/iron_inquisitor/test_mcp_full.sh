#!/bin/bash
source /root/kuroshin/venv/bin/activate

echo "=== Bridge: list_dir test ==="
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_dir","arguments":{"path":"scripts"}}}\n' \
| timeout 10 python3 /mnt/c/Kuroshin/mcp_servers/bridge_server/kuroshin_bridge_mcp.py 2>/dev/null | grep '"id":2'

echo ""
echo "=== Search: web_search test ==="
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"web_search","arguments":{"query":"python 3.13"}}}\n' \
| timeout 20 python3 /mnt/c/Kuroshin/mcp_servers/search_server/kuroshin_search_mcp.py 2>/dev/null | grep '"id":2' | head -c 300

echo ""
echo "=== Walker: walker_status test ==="
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"walker_status","arguments":{}}}\n' \
| timeout 10 python3 /mnt/c/Kuroshin/mcp_servers/walker_server/kuroshin_walker_mcp.py 2>/dev/null | grep '"id":2' | head -c 300
