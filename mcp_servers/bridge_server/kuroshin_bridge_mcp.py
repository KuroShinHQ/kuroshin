import asyncio
import sys
import json
import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

server = Server("kuroshin-bridge")

BRIDGE_URL    = "http://127.0.0.1:3005"
BRIDGE_SECRET = "kuroshin-bridge-2026"
TIMEOUT       = 15.0

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_file",
            description=(
                "[BRIDGE] C:\\Kuroshin dizinindeki herhangi bir dosyayı oku. "
                "path parametresi proje köküne göre göreceli olmalı. "
                "Örnek: 'KUROSHIN_MASTER_MEMORY.md' veya 'agents/kuroshin_walker_service.py'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Proje kökünden göreceli dosya yolu"}
                },
                "required": ["path"]
            },
        ),
        types.Tool(
            name="write_file",
            description=(
                "[BRIDGE] C:\\Kuroshin dizinine dosya yaz veya güncelle. "
                "Yazma öncesi otomatik yedek alınır (backups/agent_changes/). "
                "path: göreceli yol, content: dosya içeriği."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Proje kökünden göreceli dosya yolu"},
                    "content": {"type": "string", "description": "Yazılacak dosya içeriği"}
                },
                "required": ["path", "content"]
            },
        ),
        types.Tool(
            name="list_dir",
            description=(
                "[BRIDGE] C:\\Kuroshin dizininde klasör içeriğini listele. "
                "path boş bırakılırsa proje kökü listelenir."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Proje kökünden göreceli klasör yolu (boş = kök)"}
                },
                "required": []
            },
        ),
        types.Tool(
            name="bridge_status",
            description="[BRIDGE] Agent Bridge servisinin çalışıp çalışmadığını kontrol et.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    args = arguments or {}

    # ── bridge_status ──────────────────────────────────────────
    if name == "bridge_status":
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{BRIDGE_URL}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    return [types.TextContent(
                        type="text",
                        text=f"✅ Agent Bridge AKTIF — root: {data.get('root')} | port: {data.get('port')}"
                    )]
        except Exception as e:
            return [types.TextContent(type="text",
                text=f"❌ Agent Bridge KAPALI (port 3005) — {e}\n"
                     "Başlatmak için: Kuroshin.bat Walker Modu ile sistemi başlatın.")]

    # ── read_file ──────────────────────────────────────────────
    if name == "read_file":
        file_path = args.get("path", "").strip()
        if not file_path:
            return [types.TextContent(type="text", text="HATA: path parametresi boş olamaz.")]
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(f"{BRIDGE_URL}/read_file", params={"path": file_path})
                if resp.status_code == 200:
                    data = resp.json()
                    content  = data.get("content", "")
                    size     = data.get("size", 0)
                    truncated = data.get("truncated", False)
                    note = f"\n\n[KISALTILDI — toplam {size} karakter, ilk 12000 gösteriliyor]" if truncated else ""
                    return [types.TextContent(type="text",
                        text=f"📄 {data.get('path')}\n{'─'*50}\n{content}{note}")]
                elif resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Dosya bulunamadı: {file_path}")]
                else:
                    return [types.TextContent(type="text", text=f"Bridge HTTP {resp.status_code}: {resp.text[:200]}")]
        except httpx.ConnectError:
            return [types.TextContent(type="text",
                text="❌ Agent Bridge çalışmıyor (port 3005). Kuroshin.bat ile başlatın.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"read_file hatası: {e}")]

    # ── write_file ─────────────────────────────────────────────
    if name == "write_file":
        file_path = args.get("path", "").strip()
        content   = args.get("content", "")
        if not file_path:
            return [types.TextContent(type="text", text="HATA: path parametresi boş olamaz.")]
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{BRIDGE_URL}/write_file",
                    json={"path": file_path, "content": content, "secret": BRIDGE_SECRET},
                    headers={"Content-Type": "application/json"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [types.TextContent(type="text",
                        text=f"✅ Yazıldı: {data.get('written')}\n"
                             f"   Boyut: {data.get('size')} karakter\n"
                             f"   Yedek: backups/agent_changes/ altına alındı")]
                elif resp.status_code == 403:
                    return [types.TextContent(type="text", text="❌ Yetkisiz yazma — secret hatalı.")]
                else:
                    return [types.TextContent(type="text", text=f"Bridge HTTP {resp.status_code}: {resp.text[:200]}")]
        except httpx.ConnectError:
            return [types.TextContent(type="text",
                text="❌ Agent Bridge çalışmıyor (port 3005). Kuroshin.bat ile başlatın.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"write_file hatası: {e}")]

    # ── list_dir ───────────────────────────────────────────────
    if name == "list_dir":
        dir_path = args.get("path", "").strip()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(f"{BRIDGE_URL}/list_dir", params={"path": dir_path or ""})
                if resp.status_code == 200:
                    data    = resp.json()
                    entries = data.get("entries", [])
                    lines   = []
                    for e in entries:
                        icon = "📁" if e["type"] == "dir" else "📄"
                        lines.append(f"  {icon} {e['name']}")
                    listing = "\n".join(lines) if lines else "(boş)"
                    return [types.TextContent(type="text",
                        text=f"📂 {data.get('path')}\n{'─'*50}\n{listing}")]
                else:
                    return [types.TextContent(type="text", text=f"Bridge HTTP {resp.status_code}: {resp.text[:200]}")]
        except httpx.ConnectError:
            return [types.TextContent(type="text",
                text="❌ Agent Bridge çalışmıyor (port 3005). Kuroshin.bat ile başlatın.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"list_dir hatası: {e}")]

    return [types.TextContent(type="text", text=f"Bilinmeyen araç: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kuroshin-bridge",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
