import asyncio
import httpx
import sys
import io
import json
import re
import urllib.parse
import base64
import random
from bs4 import BeautifulSoup
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

STEALTH_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Windows UTF-8 Bypass
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

server = Server("kuroshin-smart-search")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

async def decode_google_news_url(url: str) -> str:
    """NEBULA DECODER v2.0: Decodes Base64 URLs and provides httpx fallback for redirects."""
    if "news.google.com" not in url:
        return url
    
    candidate = url
    try:
        # 1. Base64 Extraction Logic (High Speed)
        if "articles/" in url:
            token = url.split("articles/")[1].split("?")[0]
            # Precise padding to avoid binascii errors
            padded_token = token + "=" * (-len(token) % 4)
            decoded_bytes = base64.urlsafe_b64decode(padded_token)
            decoded_text = decoded_bytes.decode('latin-1', errors='ignore')
            url_match = re.search(r'(https?://[^\s\x00-\x1f\x7f-\xff"\\<>]+)', decoded_text)
            if url_match:
                candidate = url_match.group(1).split('\\')[0].split(']')[0].split('}')[0].rstrip('.')
                if "news.google.com" not in candidate:
                    return candidate

        # 2. FALLBACK: Real-time Redirect Following (High Accuracy)
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, headers=headers) as client:
            resp = await client.get(url)
            final_url = str(resp.url)
            if "news.google.com" not in final_url:
                return final_url
    except Exception:
        pass
    
    return url

def _decode_ddg_url(href: str) -> str:
    """DDG redirect URL'sinden gerçek URL'yi çıkar: //duckduckgo.com/l/?uddg=https%3A..."""
    if href.startswith("http"):
        return href
    parsed = urllib.parse.urlparse("https:" + href if href.startswith("//") else href)
    uddg = urllib.parse.parse_qs(parsed.query).get("uddg", [""])
    if uddg and uddg[0]:
        return urllib.parse.unquote(uddg[0])
    return "https:" + href if href.startswith("//") else href

async def get_duckduckgo_fallback(query: str):
    """Fallback search using DuckDuckGo HTML interface."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200: return []
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for row in soup.find_all('div', class_='result'):
                title_tag = row.find('a', class_='result__a')
                snippet_tag = row.find('a', class_='result__snippet')
                if title_tag and title_tag.get('href'):
                    real_url = _decode_ddg_url(title_tag.get('href'))
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "url": real_url,
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else ""
                    })
            return results[:5]
        except Exception:
            return []

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="web_search",
            description="[NUCLEAR SEARCH] News RSS & Technical Search with Automatic Fallback.",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        types.Tool(
            name="fetch_page",
            description="[SHIELD] Fast reading. Handles Google News redirects and anti-bot checks.",
            inputSchema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        ),
        types.Tool(
            name="fetch_page_deep",
            description="[SWORD] Crawl4AI Breach. Use if SHIELD fails or Cloudflare is detected.",
            inputSchema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        ),
        types.Tool(
            name="fetch_page_stealth",
            description="[GHOST v2] Crawl4AI engine. Cloudflare/JS korumalı siteler için. fetch_page_deep başarısız olduğunda kullan. Magic mode + anti-bot bypass.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Okunacak URL"},
                    "wait_seconds": {"type": "integer", "description": "JS render için bekleme süresi (saniye, varsayılan: 2)", "default": 2}
                },
                "required": ["url"]
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if name == "web_search":
        query = arguments.get("query")
        url = f"http://localhost:8091/search?q={urllib.parse.quote(query)}"
        results_output = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get('results', []):
                        decoded_url = await decode_google_news_url(r['url'])
                        results_output.append(f"TITLE: {r['title']}\nURL: {decoded_url}\nSOURCE: RSS-News\n---")
            except Exception as _e: print(f"[search_mcp] RSS fetch HATA: {_e}")

        if not results_output:
            ddg_results = await get_duckduckgo_fallback(query)
            for r in ddg_results:
                results_output.append(f"TITLE: {r['title']}\nURL: {r['url']}\nSNIPPET: {r['snippet']}\nSOURCE: Web-Search\n---")

        return [types.TextContent(type="text", text="\n".join(results_output[:8]) if results_output else "No results found.")]

    elif name == "fetch_page":
        url = arguments.get("url")
        url = await decode_google_news_url(url) # NEBULA DECODER MANDATORY CALL
        target_url = url
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        async def perform_deep_fetch(original_url):
            try:
                from crawl4ai import AsyncWebCrawler
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=original_url)
                    return [types.TextContent(type="text", text=f"AUTOSWITCH_SUCCESS: {original_url}\n\n{result.markdown[:15000]}")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"AutoSwitch Error: {str(e)}")]

        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers=headers) as client:
            try:
                resp = await client.get(target_url)
                # OTONOM GEÇİŞ: 403, 401 veya 429 gibi engelleme durumlarında otomatik Balyoz'a geç
                if resp.status_code in [403, 401, 429, 404]:
                    return await perform_deep_fetch(target_url)

                soup = BeautifulSoup(resp.text, "html.parser")
                for e in soup(["script", "style", "nav", "footer", "header"]): e.extract()
                content = re.sub(r'\n+', '\n', soup.get_text(separator='\n', strip=True))
                
                # OTONOM GEÇİŞ: Eğer içerik çok kısaysa (JS Required uyarısı gibi), otomatik Balyoz'a geç
                if len(content) < 500:
                    return await perform_deep_fetch(target_url)
                    
                return [types.TextContent(type="text", text=f"SOURCE: {target_url}\n\n{content[:12000]}")]
            except Exception:
                # Bağlantı hatası durumunda da otomatik Balyoz'u dene
                return await perform_deep_fetch(target_url)

    elif name == "fetch_page_deep":
        url = arguments.get("url")
        url = await decode_google_news_url(url) # NEBULA DECODER MANDATORY CALL
        target_url = url
        DEEP_FETCH_CHAR_LIMIT = 10000
        try:
            from crawl4ai import AsyncWebCrawler
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=target_url)
                content = result.markdown[:DEEP_FETCH_CHAR_LIMIT]
                truncated = len(result.markdown) > DEEP_FETCH_CHAR_LIMIT
                suffix = f"\n\n[TRUNCATED: {len(result.markdown)} karakter → {DEEP_FETCH_CHAR_LIMIT} ile sınırlandırıldı]" if truncated else ""
                return [types.TextContent(type="text", text=f"SOURCE: {target_url}\n\n{content}{suffix}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Deep Fetch Error: {str(e)}")]

    elif name == "fetch_page_stealth":
        url = arguments.get("url")
        wait_seconds = int(arguments.get("wait_seconds", 2))
        url = await decode_google_news_url(url)
        target_url = url
        STEALTH_CHAR_LIMIT = 12000

        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

            browser_cfg = BrowserConfig(
                headless=True,
                browser_type="chromium",
                user_agent=random.choice(STEALTH_USER_AGENTS),
                extra_args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=30000,
                delay_before_return_html=wait_seconds,
                magic=True,
                simulate_user=True,
                override_navigator=True,
            )

            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=target_url, config=run_cfg)

            content = result.markdown or result.cleaned_html or ""
            content = re.sub(r'\n{3,}', '\n\n', content.strip())

            if len(content) < 50:
                return [types.TextContent(type="text",
                    text=f"GHOST v2: Icerik cok kisa ({len(content)} kar). Cloudflare engelliyor olabilir.\nSOURCE: {target_url}")]

            truncated = len(content) > STEALTH_CHAR_LIMIT
            suffix = f"\n\n[GHOST TRUNCATED: {len(content)} kar → {STEALTH_CHAR_LIMIT}]" if truncated else ""
            return [types.TextContent(type="text",
                text=f"GHOST v2 (Crawl4AI) BASARILI\nSOURCE: {target_url}\n{'='*50}\n{content[:STEALTH_CHAR_LIMIT]}{suffix}")]

        except Exception as e:
            # Crawl4AI başarısız → Playwright fallback
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"])
                    ua = random.choice(STEALTH_USER_AGENTS)
                    context = await browser.new_context(user_agent=ua, viewport={"width": 1920, "height": 1080})
                    await context.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
                    page = await context.new_page()
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                    if wait_seconds > 0:
                        await asyncio.sleep(wait_seconds)
                    content = await page.inner_text("body")
                    content = re.sub(r'\n{3,}', '\n\n', content.strip())
                    await browser.close()
                    truncated = len(content) > STEALTH_CHAR_LIMIT
                    suffix = f"\n\n[PW TRUNCATED: {len(content)} kar → {STEALTH_CHAR_LIMIT}]" if truncated else ""
                    return [types.TextContent(type="text",
                        text=f"GHOST PLAYWRIGHT FALLBACK\nSOURCE: {target_url}\n{'='*50}\n{content[:STEALTH_CHAR_LIMIT]}{suffix}")]
            except Exception as e2:
                return [types.TextContent(type="text", text=f"GHOST HATA (Crawl4AI: {str(e)}) (Playwright: {str(e2)})\nSOURCE: {target_url}")]

    return [types.TextContent(type="text", text="Unknown tool.")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kuroshin-smart-search",
                server_version="4.5.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
