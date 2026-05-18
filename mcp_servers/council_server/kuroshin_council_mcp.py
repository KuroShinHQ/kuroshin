import asyncio
import sys
import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

server = Server("kuroshin-council")

COUNCIL_URL = "http://127.0.0.1:9004"
TIMEOUT     = 180.0


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="council_teknisyen",
            description=(
                "[KONSEY: TEKNİSYEN] Kod yazma, dosya okuma/düzenleme, shell komutları. "
                "Smolagents CodeAgent — Python araçlarıyla çalışır. "
                "Örnek: 'şu scripti incele ve hatayı bul', 'disk kullanımını göster'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Teknisyen ajana verilecek görev"}
                },
                "required": ["task"]
            },
        ),
        types.Tool(
            name="council_gozcu",
            description=(
                "[KONSEY: GÖZCÜ] Web tarama, GitHub/HuggingFace hype takibi, yeni teknoloji keşfi. "
                "Smolagents + DuckDuckGo arama. "
                "Örnek: 'bu hafta GitHub trending AI projeleri neler', 'Qwen3 çıktı mı kontrol et'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Gözcü ajana verilecek araştırma görevi"}
                },
                "required": ["task"]
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    args = arguments or {}
    task = args.get("task", "").strip()
    if not task:
        return [types.TextContent(type="text", text="HATA: task boş olamaz.")]

    if name == "council_teknisyen":
        agent = "teknisyen"
        prefix = "⚙️ TEKNİSYEN RAPORU"
    elif name == "council_gozcu":
        agent = "gozcu"
        prefix = "🔭 GÖZCÜ RAPORU"
    else:
        return [types.TextContent(type="text", text=f"Bilinmeyen araç: {name}")]

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{COUNCIL_URL}/task",
                json={"agent": agent, "task": task},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data    = resp.json()
                result  = data.get("result", "")
                elapsed = data.get("elapsed", "?")
                return [types.TextContent(type="text",
                    text=f"{prefix} ({elapsed}s)\n{'='*40}\n{result}")]
            else:
                return [types.TextContent(type="text",
                    text=f"Konsey HTTP {resp.status_code}: {resp.text[:300]}")]

    except httpx.ConnectError:
        return [types.TextContent(type="text",
            text="❌ Ajan Konseyi çalışmıyor (port 9004).\nKuroshin.bat → [1] Walker Modu ile başlatın.")]
    except httpx.TimeoutException:
        return [types.TextContent(type="text",
            text=f"⏱️ Konsey zaman aşımı ({TIMEOUT}sn).")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Konsey hatası: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name="kuroshin-council",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
