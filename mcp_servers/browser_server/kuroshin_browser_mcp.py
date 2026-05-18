#!/usr/bin/env python3
"""
Kuroshin Browser MCP Server v5.0
browser-use kaldirildi — gereksiz ve yerel model icin cok agir.
Araclar: open_url (Windows), browser_screenshot, browser_fetch (Playwright headless)
"""
import asyncio
import json
import os
import subprocess
import urllib.request

from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent

AGENT_BRIDGE = "http://127.0.0.1:3005"

server = Server("kuroshin-browser")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="open_url",
            description="Windows tarayicisinda URL ac. Direkt http/https URL ver.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Acilacak URL (http/https)"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="youtube_play",
            description=(
                "YouTube'da muzik/video ara ve Windows tarayicisinda AC. "
                "Kullanici 'YouTubede X ac/cal' dediginde bu araci kullan. "
                "Otomatik olarak YouTube'da arar ve en iyi eslesen videoyu acar."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Aranacak sarki/video adi, sanatci vs."}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="browser_fetch",
            description="Bir URL'den sayfa icerigini oku (JS gerektiren siteler dahil). Veri cekme icin kullan, URL acmak icin degil.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="browser_screenshot",
            description="Bir URL'nin ekran goruntusunu al ve kaydet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "output_path": {"type": "string", "default": "/mnt/c/Kuroshin/logs/screenshot.png"}
                },
                "required": ["url"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "open_url":
        return await open_url(arguments)
    elif name == "youtube_play":
        return await youtube_play(arguments)
    elif name == "browser_fetch":
        return await browser_fetch(arguments)
    elif name == "browser_screenshot":
        return await browser_screenshot(arguments)
    return [TextContent(type="text", text=f"Bilinmeyen arac: {name}")]


async def open_url(args: dict):
    url = args.get("url", "").strip()
    if not url or not url.startswith("http"):
        return [TextContent(type="text", text="Gecersiz URL.")]

    # Once Agent Bridge dene (Windows process)
    try:
        payload = json.dumps({"url": url}).encode()
        req = urllib.request.Request(
            f"{AGENT_BRIDGE}/open_url",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            resp = json.loads(r.read())
        if resp.get("ok"):
            return [TextContent(type="text", text=f"Acildi: {url}")]
    except Exception:
        pass

    # Fallback: cmd.exe dogrudan
    try:
        subprocess.Popen(
            ["/mnt/c/Windows/System32/cmd.exe", "/c", "start", "", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return [TextContent(type="text", text=f"Acildi: {url}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Acma hatasi: {str(e)[:200]}")]


async def youtube_play(args: dict):
    """YouTube'da ara, ilk video URL'sini bul, Windows'ta ac."""
    query = args.get("query", "").strip()
    if not query:
        return [TextContent(type="text", text="Sorgu bos.")]

    # YouTube Data API yoksa yt-dlp ile ara, o da yoksa search URL'si ac
    video_url = None

    # yt-dlp ile ilk sonucu al (WSL'de kurulu olabilir)
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-playlist", "--get-id", f"ytsearch1:{query}"],
            capture_output=True, text=True, timeout=15
        )
        video_id = result.stdout.strip().split("\n")[0]
        if video_id and len(video_id) == 11:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        pass

    # yt-dlp yoksa search sayfasini ac
    if not video_url:
        safe_query = query.replace(" ", "+").replace("'", "%27")
        video_url = f"https://www.youtube.com/results?search_query={safe_query}"

    return await open_url({"url": video_url})


async def browser_fetch(args: dict):
    url = args.get("url", "")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=15000)
            content = await page.inner_text("body")
            await browser.close()
        return [TextContent(type="text", text=content[:8000])]
    except Exception as e:
        return [TextContent(type="text", text=f"Fetch hatasi: {str(e)[:300]}")]


async def browser_screenshot(args: dict):
    url = args.get("url", "")
    output = args.get("output_path", "/mnt/c/Kuroshin/logs/screenshot.png")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=15000)
            await page.screenshot(path=output)
            await browser.close()
        return [TextContent(type="text", text=f"Screenshot: {output}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Screenshot hatasi: {str(e)[:300]}")]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
