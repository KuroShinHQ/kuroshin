#!/bin/bash
source /root/kuroshin/venv/bin/activate

echo "=== Bridge MCP Hata Testi ==="
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"read_file","arguments":{"path":"agents/kuroshin_chancellor.py"}}}' \
| timeout 10 python3 /mnt/c/Kuroshin/mcp_servers/bridge_server/kuroshin_bridge_mcp.py 2>&1 | head -30

echo ""
echo "=== Search MCP Hata Testi ==="
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"web_search","arguments":{"query":"python test"}}}' \
| timeout 15 python3 /mnt/c/Kuroshin/mcp_servers/search_server/kuroshin_search_mcp.py 2>&1 | head -20
