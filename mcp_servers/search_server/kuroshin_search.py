import asyncio
import httpx
import re
import sys
import io
import urllib.parse
import base64
import random
import logging

# TÜM LOGLARI VE ÇIKTILARI SUSTUR (Stdio kirliliğini engelle)
logging.basicConfig(level=logging.CRITICAL)
sys.stderr = io.StringIO() 

try:
    from bs4 import BeautifulSoup
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types
except ImportError:
    # Eğer kütüphane eksikse sessizce ölme, hata basma (MCP JSON-RPC'yi bozma)
    sys.exit(1)

# Force UTF-8 for stdio
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

server = Server("kuroshin-search")

def decode_google_news_url(url: str) -> str:
    if "news.google.com/rss/articles/" not in url: return url
    try:
        token = url.split("articles/")[1].split("?")[0]
        decoded_bytes = base64.urlsafe_b64decode(token + "====")
        decoded_text = decoded_bytes.decode('latin-1', errors='ignore')
        url_match = re.search(r'(https?://[^\s\x00-\x1f\x7f-\xff"\\<>]+)', decoded_text)
        if url_match: return re.split(r'[\\\)\]\}\x00-\x08]', url_match.group(1))[0].rstrip('.').rstrip(';')
        return url
    except: return url

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="web_search", description="Search the web.", inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        types.Tool(name="fetch_page", description="Read a page.", inputSchema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if name == "web_search":
        query = arguments.get("query")
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for row in soup.find_all('div', class_='result'):
                    a = row.find('a', class_='result__a')
                    if a: results.append(f"TITLE: {a.get_text()}\nURL: {decode_google_news_url(a.get('href'))}\n---")
                return [types.TextContent(type="text", text="\n".join(results[:5]) or "No results.")]
            except: return [types.TextContent(type="text", text="Search failed.")]
    elif name == "fetch_page":
        target = decode_google_news_url(arguments.get("url"))
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            try:
                resp = await client.get(target, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(resp.text, "html.parser")
                for e in soup(["script", "style"]): e.extract()
                return [types.TextContent(type="text", text=soup.get_text()[:10000])]
            except: return [types.TextContent(type="text", text="Fetch failed.")]
    return []

async def main():
    try:
        async with stdio_server() as (read_stream, write_stream):
            # MULTI-VERSION COMPATIBILITY: Try different capability structures
            try:
                # Latest Version
                init_options = InitializationOptions(
                    server_name="kuroshin-search",
                    server_version="2.5.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    )
                )
            except:
                # Fallback to simple Initialization (older versions)
                init_options = InitializationOptions(
                    server_name="kuroshin-search",
                    server_version="2.5.0",
                    capabilities=server.get_capabilities()
                )

            await server.run(read_stream, write_stream, init_options)
    except:
        pass # Silent death to avoid stdio corruption

if __name__ == "__main__":
    asyncio.run(main())
