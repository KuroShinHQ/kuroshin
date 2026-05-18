#!/usr/bin/env python3
"""MCP sunucularını direkt test et ve tam stdout/stderr göster."""
import subprocess, json, sys

VENV_PY = "/root/kuroshin/venv/bin/python3"
BASE = "/mnt/c/Kuroshin/mcp_servers"

servers = {
    "bridge": f"{BASE}/bridge_server/kuroshin_bridge_mcp.py",
    "search": f"{BASE}/search_server/kuroshin_search_mcp.py",
    "walker": f"{BASE}/walker_server/kuroshin_walker_mcp.py",
}

calls = {
    "bridge": ("list_dir", {"path": "scripts"}),
    "search": ("web_search", {"query": "python 3.13"}),
    "walker": ("walker_status", {}),
}

for name, script in servers.items():
    tool, args = calls[name]
    print(f"\n{'='*50}")
    print(f"TEST: {name} → {tool}({args})")

    lines = [
        json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize",
            "params":{"protocolVersion":"2024-11-05","capabilities":{},
                      "clientInfo":{"name":"test","version":"1"}}}),
        json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"}),
        json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/call",
            "params":{"name":tool,"arguments":args}}),
    ]
    inp = "\n".join(lines) + "\n"

    try:
        proc = subprocess.Popen(
            [VENV_PY, script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8"
        )
        stdout, stderr = proc.communicate(input=inp, timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        print("TIMEOUT!")

    print(f"STDOUT ({len(stdout)} chars):")
    for line in stdout.strip().splitlines():
        print(f"  {line[:200]}")

    print(f"STDERR (last 5 lines):")
    serr_lines = [l for l in stderr.strip().splitlines() if l.strip()]
    for line in serr_lines[-5:]:
        print(f"  {line}")
