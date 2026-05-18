"""
DeerFlow MCP Server v2.0 — Bağımsız araştırma motoru
Bağımlılıklar: deerflow_core.py subprocess'i YOK.
Tüm mantık burada: DuckDuckGo → Crawl4AI → Crawlee fallback → Qwen3 analiz → ChromaDB cache.
"""
import asyncio
import sys
import json
import re
import time
import hashlib
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from kuroshin_security import sanitize_web_content
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

server = Server("kuroshin-deerflow")

LLAMA_URL    = "http://127.0.0.1:8080/v1/chat/completions"
LITELLM_URL  = "http://127.0.0.1:6000/v1/chat/completions"
CRAWLEE_URL  = "http://127.0.0.1:3006/crawl"
WALKER_URL   = "http://127.0.0.1:9002"
CHROMA_DIR   = "/root/kuroshin/memory/chroma"
TIMEOUT_LLM  = 60
TIMEOUT_WEB  = 20
TIMEOUT_WALK = 300

# ── Araç listesi ───────────────────────────────────────────────────────────────

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="deerflow_research",
            description=(
                "[DEERFLOW v2.0] Otonom derin araştırma motoru. "
                "DuckDuckGo ile arama → Crawl4AI/Crawlee ile çoklu kaynak okuma → "
                "Gemma4 ile Türkçe istihbarat raporu. ChromaDB'ye otomatik kaydeder. "
                "Hava durumu da desteklenir ('İstanbul hava durumu')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Araştırılacak konu (Türkçe veya İngilizce)"
                    },
                    "sources": {
                        "type": "integer",
                        "description": "Okunacak kaynak sayısı (1-3, varsayılan 2)",
                        "default": 2
                    }
                },
                "required": ["query"]
            },
        ),
        types.Tool(
            name="walker_deep_research",
            description=(
                "[WALKER+DEERFLOW] Walker Agent üzerinden derin araştırma. "
                "Walker; arama + web okuma + ChromaDB hafıza yazma zincirini tam otonom çalıştırır. "
                "deerflow_research'ten daha kapsamlı ama daha yavaş (60-120sn). "
                "Kritik araştırmalar ve hafızaya kaydedilmesi gereken bilgiler için kullan."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Walker'a verilecek araştırma görevi"}
                },
                "required": ["task"]
            },
        ),
    ]

# ── Yardımcı fonksiyonlar ───────────────────────────────────────────────────────

async def _llm(prompt: str) -> str:
    payload = {
        "model": "gemma4",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.1,
    }
    headers = {"Content-Type": "application/json", "Authorization": "Bearer kuroshin-secret"}
    async with httpx.AsyncClient() as client:
        for url in [LITELLM_URL, LLAMA_URL]:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=TIMEOUT_LLM)
                if r.status_code == 200:
                    msg = r.json()["choices"][0]["message"]
                    return (msg.get("reasoning_content") or msg.get("content", "")).strip()
            except Exception:
                pass
    return ""


async def _fetch_crawl4ai(url: str) -> str:
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        cfg = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(threshold=0.45, threshold_type="fixed", min_word_threshold=10),
                options={"ignore_links": True, "ignore_images": True, "extract_main_content": True}
            ),
            page_timeout=15000,
            remove_overlay_elements=True,
            word_count_threshold=40,
        )
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await asyncio.wait_for(crawler.arun(url=url, config=cfg), timeout=TIMEOUT_WEB)
            if result.success and result.markdown:
                return sanitize_web_content(result.markdown, max_chars=4000)
    except Exception:
        pass
    return ""


async def _fetch_crawlee(url: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(CRAWLEE_URL, json={"url": url, "mode": "simple"}, timeout=TIMEOUT_WEB)
            if r.status_code == 200:
                raw = r.json().get("content", "")
                return sanitize_web_content(raw, max_chars=4000)
    except Exception:
        pass
    return ""


async def _fetch_url(url: str) -> str:
    content = await _fetch_crawl4ai(url)
    if not content:
        content = await _fetch_crawlee(url)
    return content


async def _chroma_save(query: str, report: str):
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        col = client.get_or_create_collection("kuroshin_memory")
        doc_id = "deerflow_" + hashlib.md5(query.encode()).hexdigest()[:12]
        col.upsert(
            ids=[doc_id],
            documents=[f"[DeerFlow] {query}\n\n{report}"],
            metadatas=[{"source": "deerflow_v2", "ts": str(int(time.time()))}]
        )
    except Exception:
        pass


async def _weather(city: str) -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["curl", "-s", f"wttr.in/{city}?format=%l:+%t+%C+%w&lang=tr"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            return f"🌍 {city.upper()} HAVA DURUMU:\n{r.stdout.strip()}"
    except Exception:
        pass
    return f"⚠️ {city} için hava durumu alınamadı."


async def _deep_research(query: str, n_sources: int = 2) -> str:
    from ddgs import DDGS
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=min(n_sources + 1, 4)))
    except Exception as e:
        return f"❌ DuckDuckGo arama hatası: {e}"

    if not hits:
        return "Bu konuda açık kaynaklarda bilgi bulunamadı."

    fetched = []
    for hit in hits[:n_sources]:
        url = hit.get("href", "")
        if not url:
            continue
        content = await _fetch_url(url)
        if content:
            fetched.append((url, content))

    if not fetched:
        snippet = hits[0].get("body", "")
        return f"🔍 Web içeriği okunamadı. DDG özeti:\n{snippet}"

    combined = "\n\n---\n\n".join(
        f"KAYNAK: {url}\n{text[:2000]}" for url, text in fetched
    )

    prompt = (
        f"Aşağıdaki web içeriğini analiz ederek şu soruyu yanıtla: {query}\n\n"
        f"Kurallар:\n"
        f"- Menü/reklam/nav metinlerini yoksay\n"
        f"- Sadece soruyla ilgili net bilgileri çıkar\n"
        f"- Türkçe, maksimum 4 paragraf\n\n"
        f"=== KAYNAKLAR ===\n{combined[:5000]}"
    )
    analysis = await _llm(prompt)
    if not analysis:
        analysis = fetched[0][1][:800]

    sources_line = " | ".join(url for url, _ in fetched)
    report = (
        f"🦌 DEERFLOW v2.0 ARAŞTIRMA RAPORU\n"
        f"{'='*45}\n"
        f"🎯 Sorgu: {query}\n"
        f"🔗 Kaynaklar: {sources_line}\n\n"
        f"📄 ANALİZ:\n{analysis}\n\n"
        f"✅ {len(fetched)} kaynak okundu, analiz tamamlandı."
    )
    return report

# ── Araç işleyici ───────────────────────────────────────────────────────────────

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    args = arguments or {}

    if name == "deerflow_research":
        query = args.get("query", "").strip()
        if not query:
            return [types.TextContent(type="text", text="HATA: query parametresi boş olamaz.")]
        n_sources = max(1, min(3, int(args.get("sources", 2))))

        query_lower = query.lower()
        if any(w in query_lower for w in ["hava", "weather", "meteoroloji", "sıcaklık", "derece"]):
            city = re.sub(r"(hava|durumu|sıcaklık|derece|nedir|nasıl|weather|temperature|için)", "", query_lower).strip()
            result = await _weather(city or "Istanbul")
        else:
            result = await _deep_research(query, n_sources)
            asyncio.create_task(_chroma_save(query, result))

        return [types.TextContent(type="text", text=result)]

    if name == "walker_deep_research":
        task = args.get("task", "").strip()
        if not task:
            return [types.TextContent(type="text", text="HATA: task parametresi boş olamaz.")]
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_WALK) as client:
                resp = await client.post(f"{WALKER_URL}/task", json={"task": task},
                                         headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    data = resp.json()
                    result  = data.get("result", "")
                    elapsed = data.get("elapsed", "?")
                    mem_id  = data.get("memory_id")
                    mem_note = f"\n💾 ChromaDB'ye kaydedildi (ID: {mem_id})" if mem_id else ""
                    return [types.TextContent(type="text",
                        text=f"🦅 WALKER DERİN ARAŞTIRMA ({elapsed}s)\n{'='*45}\n{result}{mem_note}")]
                return [types.TextContent(type="text",
                    text=f"Walker HTTP {resp.status_code}: {resp.text[:300]}")]
        except httpx.ConnectError:
            return [types.TextContent(type="text",
                text="❌ Walker servisi çalışmıyor (port 9002). Kuroshin.bat → [1] ile başlatın.")]
        except httpx.TimeoutException:
            return [types.TextContent(type="text",
                text=f"⏱️ Walker zaman aşımı ({TIMEOUT_WALK}sn).")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Walker hatası: {e}")]

    return [types.TextContent(type="text", text=f"Bilinmeyen araç: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kuroshin-deerflow",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
