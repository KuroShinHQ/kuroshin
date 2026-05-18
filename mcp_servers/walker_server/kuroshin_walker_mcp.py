import asyncio
import sys
import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Windows UTF-8 Bypass
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

server = Server("kuroshin-walker")

WALKER_BASE_URL = "http://127.0.0.1:9002"  # 9001 Windows rezerve — port 9002
WALKER_TIMEOUT  = 300.0  # Walker otonom araştırma yapıyor, uzun sürebilir

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="walker_task",
            description=(
                "[WALKER AGENT] Otonom araştırma ajanına görev ver. "
                "Walker internette arama yapar, sayfaları okur, analiz eder ve sonuçları ChromaDB kuroshin_memory koleksiyonuna kaydeder. Geçmiş araştırmaları sorgulamak için chroma_query_documents collection_name=kuroshin_memory kullan. "
                "Karmaşık araştırma görevleri için kullan. "
                "Örnek: 'AutoGen çoklu ajan mimarisini araştır ve özetle'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Walker'a verilecek araştırma görevi (Türkçe veya İngilizce)"
                    }
                },
                "required": ["task"]
            },
        ),
        types.Tool(
            name="walker_status",
            description="[WALKER STATUS] Walker Agent servisinin çalışıp çalışmadığını kontrol et.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:

    if name == "walker_status":
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{WALKER_BASE_URL}/status")
                if resp.status_code == 200:
                    data = resp.json()
                    return [types.TextContent(
                        type="text",
                        text=f"✅ Walker AKTIF — mode: {data.get('mode')}, model: {data.get('model')}"
                    )]
                else:
                    return [types.TextContent(type="text", text=f"⚠️ Walker yanıt verdi ama HTTP {resp.status_code}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"❌ Walker KAPALI — {e}\nBaşlatmak için: Kuroshin.bat → [1] Walker Modu")]

    if name == "walker_task":
        task = (arguments or {}).get("task", "").strip()
        if not task:
            return [types.TextContent(type="text", text="HATA: task parametresi boş olamaz.")]

        try:
            async with httpx.AsyncClient(timeout=WALKER_TIMEOUT) as client:
                resp = await client.post(
                    f"{WALKER_BASE_URL}/task",
                    json={"task": task},
                    headers={"Content-Type": "application/json"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result  = data.get("result", "")
                    elapsed = data.get("elapsed", "?")
                    mem_id  = data.get("memory_id", None)
                    mem_note = f"\n💾 ChromaDB'ye kaydedildi (ID: {mem_id})" if mem_id else ""
                    return [types.TextContent(
                        type="text",
                        text=f"🦅 WALKER RAPORU ({elapsed}s)\n{'='*40}\n{result}{mem_note}"
                    )]
                else:
                    return [types.TextContent(type="text", text=f"Walker HTTP hatası: {resp.status_code}\n{resp.text[:500]}")]

        except httpx.ConnectError:
            return [types.TextContent(
                type="text",
                text="❌ Walker servisi çalışmıyor (port 9001 kapalı).\nKuroshin.bat → [1] Walker Modu ile başlatın."
            )]
        except httpx.TimeoutException:
            return [types.TextContent(type="text", text="⚠️ Walker zaman aşımı (300s). Görev çok karmaşık olabilir.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Walker hatası: {e}")]

    return [types.TextContent(type="text", text=f"Bilinmeyen araç: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kuroshin-walker",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
