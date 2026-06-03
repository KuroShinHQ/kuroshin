"""
Kuroshin Walker Service v3.0 — Agno Framework
==============================================
Agno 2.5.16 üzerine yeniden yazıldı.
- SQLite tabanlı oturum hafızası (search_past_sessions)
- Modüler araç sistemi
- ChromaDB persistent hafıza
- Port 9002, MCP wrapper değişmedi
"""

import asyncio
import re
import sys
import time
import uuid
import json
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from kuroshin_security import sanitize_web_content

import chromadb
import httpx
import uvicorn
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai.like import OpenAILike
from crawl4ai import AsyncWebCrawler
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─────────────────────────────────────────
# SABİTLER
# ─────────────────────────────────────────
SERVICE_PORT     = 9002
CRAWL_CHAR_LIMIT = 8000
MAX_OUTPUT_TOKENS = 4096
LLAMA_BASE_URL   = "http://127.0.0.1:8080/v1"
_STATE_FILE = Path("/mnt/c/Kuroshin/memory/active_model.json")
def _load_active_model() -> str:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8")).get("active_model", "")
    except Exception:
        pass
    return ""
LLAMA_MODEL      = _load_active_model() or "Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf"
CHROMA_DATA_DIR  = "/root/kuroshin/memory/walker_chroma"
SQLITE_DB_PATH   = "/root/kuroshin/memory/walker_sessions.db"
WALKER_LOG_PATH  = "/root/kuroshin/logs/walker.log"
CRAWLEE_BRIDGE_URL = "http://127.0.0.1:3006/crawl"
CRAWLEE_TIMEOUT    = 45

# ─────────────────────────────────────────
# LOG SETUP — tee fonksiyon (stdout redirect bozuyor, doğrudan dosyaya yaz)
# ─────────────────────────────────────────
Path(WALKER_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
_log_file = open(WALKER_LOG_PATH, "a", encoding="utf-8", buffering=1)

def _log(msg: str):
    print(msg, flush=True)
    try:
        _log_file.write(msg + "\n")
        _log_file.flush()
    except Exception:
        pass

# ─────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────
gemma4 = OpenAILike(
    id=LLAMA_MODEL,
    api_key="dummy",
    base_url=LLAMA_BASE_URL,
    timeout=300,
    max_tokens=MAX_OUTPUT_TOKENS,
)

# ─────────────────────────────────────────
# HAFIZA: ChromaDB Persistent
# ─────────────────────────────────────────
Path(CHROMA_DATA_DIR).mkdir(parents=True, exist_ok=True)
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)
    memory_col = chroma_client.get_or_create_collection("kuroshin_memory")
    _MEMORY_OK = True
    print(f"[HAFIZA] ChromaDB persistent aktif: {CHROMA_DATA_DIR}")
except Exception as e:
    print(f"[WARN] ChromaDB bağlantısı kurulamadı: {e}")
    memory_col = None
    _MEMORY_OK = False

# ─────────────────────────────────────────
# ARAÇLAR
# ─────────────────────────────────────────
def ddg_search(query: str) -> str:
    """İnternette arama yap. query: aranacak konu."""
    from duckduckgo_search import DDGS
    print(f"[WALKER TOOL] İnternet Aranıyor: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "Sonuç bulunamadı."
        lines = []
        for r in results:
            lines.append(f"BAŞLIK: {r.get('title', '')}")
            lines.append(f"URL: {r.get('href', '')}")
            lines.append(f"ÖZET: {r.get('body', '')[:300]}")
            lines.append("---")
        return "\n".join(lines)
    except Exception as e:
        return f"Arama hatası: {e}"


def _camoufox_fetch(url: str) -> str:
    """Camoufox hayalet Firefox ile sayfa çek — anti-bot bypass."""
    from camoufox.sync_api import Camoufox
    _log(f"[CAMOUFOX] Hayalet Firefox başlatılıyor: {url}")
    try:
        with Camoufox(headless=True) as fox:
            page = fox.new_page()
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            html = page.content()
            page.close()
        # HTML → düz metin (script/style temizle)
        import re as _re
        text = _re.sub(r'<script[\s\S]*?</script>', '', html, flags=_re.IGNORECASE)
        text = _re.sub(r'<style[\s\S]*?</style>', '', text, flags=_re.IGNORECASE)
        text = _re.sub(r'<[^>]+>', ' ', text)
        text = _re.sub(r'\s+', ' ', text).strip()
        _log(f"[CAMOUFOX] Başarılı: {len(text)} karakter")
        return text[:CRAWL_CHAR_LIMIT]
    except Exception as e:
        raise RuntimeError(f"Camoufox hatası: {e}")


def web_reader_tool(url: str) -> str:
    """Bir web sayfasını oku ve içeriğini döndür. url: okunacak sayfa."""
    print(f"[WALKER TOOL] Web Okunuyor: {url}")
    # 1. Crawl4AI
    try:
        result = asyncio.get_event_loop().run_until_complete(_fetch(url))
        if result and "Sayfa okunamadı" not in result:
            return result
        raise Exception("Crawl4AI boş döndü")
    except Exception as e1:
        _log(f"[WEB_READER] Crawl4AI başarısız ({e1}), Camoufox deneniyor...")
    # 2. Camoufox fallback
    try:
        return _camoufox_fetch(url)
    except Exception as e2:
        return f"Okuma hatası (Crawl4AI + Camoufox): {e2}"


async def _fetch(url: str) -> str:
    from crawl4ai import CrawlerRunConfig
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    run_cfg = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.48, threshold_type="fixed", min_word_threshold=10
            ),
            options={"ignore_links": True},
        ),
        page_timeout=20000,
        wait_until="domcontentloaded",
    )
    async with AsyncWebCrawler(verbose=False) as crawler:
        res = await crawler.arun(url=url, config=run_cfg)
    if res.success and res.markdown_v2:
        md = res.markdown_v2.fit_markdown or res.markdown_v2.raw_markdown
        return sanitize_web_content(md, max_chars=CRAWL_CHAR_LIMIT)
    return f"Sayfa okunamadı: {url}"


def crawlee_deep_crawl(url: str, mode: str = "playwright") -> str:
    """JavaScript-heavy siteleri Crawlee ile crawl et. mode: simple|playwright|stealth
    BORC-4-bis (2 Haz 2026): her katman sonrası _is_blocked_response check
    → short-content/CF-sig varsa exception fırlat, bir sonraki katmana düş."""
    _log(f"[WALKER TOOL] Crawlee Deep Crawl: {url} (mod: {mode})")
    try:
        resp = httpx.post(
            CRAWLEE_BRIDGE_URL,
            json={"url": url, "mode": mode},
            timeout=CRAWLEE_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "")
            elapsed = data.get("elapsed", "?")
            _log(f"[CRAWLEE] {len(content)} karakter ({elapsed}s, mod: {data.get('mode', mode)})")
            # BORC-4-bis: short-content / CF interstitial check
            if _is_blocked_response(content):
                _log(f"[BLOCKED_RESPONSE] Crawlee donus blocked (chars={len(content)} < 500 veya CF sig) → Crawl4AI fallback")
                raise Exception("Crawlee blocked-response (short-content/CF-sig)")
            if content:
                return sanitize_web_content(content, max_chars=CRAWL_CHAR_LIMIT)
            return f"Crawlee içerik üretemedi: {url}"
        raise Exception(f"HTTP {resp.status_code}")
    except Exception as e:
        _log(f"[CRAWLEE] Hata ({e}), Crawl4AI fallback: {url}")
        # 2. Crawl4AI fallback
        try:
            try:
                result = asyncio.get_event_loop().run_until_complete(_fetch(url))
            except Exception:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(_fetch(url))
                loop.close()
            if result and "Sayfa okunamadı" not in result:
                # BORC-4-bis: Crawl4AI dönüş block-sig check
                if _is_blocked_response(result):
                    _log(f"[BLOCKED_RESPONSE] Crawl4AI donus blocked → Camoufox fallback")
                    raise Exception("Crawl4AI blocked-response")
                return result
            raise Exception("Crawl4AI boş döndü")
        except Exception as e2:
            _log(f"[CRAWLEE] Crawl4AI de başarısız ({e2}), Camoufox deneniyor...")
        # 3. Camoufox 3. fallback
        try:
            cam_result = _camoufox_fetch(url)
            # BORC-4-bis: Camoufox da CF interstitial dönebilir (58 char "Just a moment")
            if _is_blocked_response(cam_result):
                _log(f"[BLOCKED_RESPONSE] Camoufox donus blocked (chars={len(cam_result or '')}) → kuroshin_scraper fallback")
                raise Exception("Camoufox blocked-response (Sahibinden tipi)")
            return cam_result
        except Exception as e3:
            _log(f"[CRAWLEE] Camoufox da başarısız ({e3}), kuroshin_scraper son fallback deneniyor...")
        # 4. BORÇ-4 (2 Haz 2026) kuroshin_scraper son fallback — 8 anti-bot signature + UA rotate
        try:
            import sys as _sys_sc
            if "/mnt/c/Kuroshin/scripts" not in _sys_sc.path:
                _sys_sc.path.insert(0, "/mnt/c/Kuroshin/scripts")
            from kuroshin_scraper import ResilientFetcher as _ResF
            _scraper = _ResF()
            _res = _scraper.get(url)
            if _res.status_code == 200 and len(_res.text or "") > 200:
                _sig = ",".join(_res.antibot_detected) if _res.antibot_detected else "none"
                _log(f"[SCRAPER_FALLBACK] url={url[:60]} sig={_sig} status=200 chars={len(_res.text)} attempts={_res.attempts}")
                return sanitize_web_content(_res.text, max_chars=CRAWL_CHAR_LIMIT)
            _log(f"[SCRAPER_FALLBACK] başarısız url={url[:60]} status={_res.status_code} chars={len(_res.text or '')}")
            return f"Crawlee + Crawl4AI + Camoufox + Scraper dördü de başarısız (scraper status={_res.status_code})"
        except Exception as e4:
            return f"Crawlee + Crawl4AI + Camoufox + Scraper dördü de başarısız: {e4}"


def save_to_memory(data: str) -> str:
    """Önemli bilgileri kalıcı hafızaya kaydet. data: kaydedilecek bilgi."""
    if not _MEMORY_OK or memory_col is None:
        return "[WARN] ChromaDB bağlı değil."
    try:
        doc_id = f"walker_{uuid.uuid4().hex[:8]}"
        memory_col.upsert(
            documents=[data[:4000]],
            ids=[doc_id],
            metadatas=[{"source": "walker_v3", "ts": str(int(time.time()))}],
        )
        print(f"[HAFIZA] Kaydedildi: {doc_id}", flush=True)
        return f"Hafızaya mühürlendi (ID: {doc_id})."
    except Exception as e:
        return f"Hafıza yazma hatası: {e}"


def _rerank_docs(query: str, docs: list, top_n: int = 3) -> list:
    """BGE-Reranker servisi varsa kullan, yoksa olduğu gibi döndür."""
    _log(f"[RERANKER] Çağrılıyor: {len(docs)} döküman, top_n={top_n}")
    try:
        resp = httpx.post(
            "http://127.0.0.1:9003/rerank",
            json={"query": query, "documents": docs, "top_n": top_n},
            timeout=10,
        )
        if resp.status_code == 200:
            ranked = resp.json().get("ranked", [])
            reranked = [r["document"] for r in ranked]
            _log(f"[RERANKER] {len(docs)} → {len(reranked)} döküman filtrelendi")
            return reranked
        _log(f"[RERANKER] HTTP {resp.status_code} hatası")
    except Exception as e:
        _log(f"[RERANKER] İstisna: {e}")
    return docs[:top_n]


def load_from_memory(query: str) -> str:
    """Geçmiş araştırmaları hafızadan sorgula. query: aranacak konu."""
    if not _MEMORY_OK or memory_col is None:
        return "[WARN] ChromaDB bağlı değil."
    try:
        results = memory_col.query(
            query_texts=[query], n_results=10, include=["documents"]
        )
        docs = results.get("documents", [[]])[0]
        _log(f"[HAFIZA] ChromaDB sorgu sonucu: {len(docs)} döküman")
        if not docs:
            return "Hafızada ilgili kayıt bulunamadı."
        # Reranker ile filtrele (10 → 3)
        docs = _rerank_docs(query, docs, top_n=3)
        lines = [f"[{i+1}] {d[:600]}" for i, d in enumerate(docs)]
        return "HAFIZA KAYITLARI:\n" + "\n---\n".join(lines)
    except Exception as e:
        return f"Hafıza okuma hatası: {e}"


# ─────────────────────────────────────────
# AGNO WALKER AGENT v3.0
# ─────────────────────────────────────────
Path(SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

walker_agent = Agent(
    model=gemma4,
    name="KuroshinWalker",
    description=(
        "Sen Kuroshin İmparatorluğu'nun Otonom Web Gözcüsü ve Baş Araştırmacısısın.\n\n"
        "ÇALIŞMA PRENSİBİ:\n"
        "1. Önce 'load_from_memory' ile geçmiş araştırmalara bak.\n"
        "2. Yeni bilgi gerekiyorsa 'ddg_search' ile interneti tara.\n"
        "3. Basit HTML siteler için 'web_reader_tool' ile oku.\n"
        "4. JavaScript ağır veya anti-bot korumalı siteler için 'crawlee_deep_crawl' kullan "
        "(mode='playwright' veya 'stealth'). Hafif siteler için mode='simple'.\n"
        "5. Analiz et, Lorduma rapor sun.\n"
        "6. Kritik bulguları MUTLAKA 'save_to_memory' ile kaydet.\n\n"
        "ÜSLUP: Ciddi, teknik, Türkçe. 'Lordum' diye hitap et."
    ),
    tools=[ddg_search, web_reader_tool, crawlee_deep_crawl, save_to_memory, load_from_memory],
    db=SqliteDb(db_file=SQLITE_DB_PATH),
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    add_history_to_context=True,
    num_history_runs=3,
    markdown=False,
    debug_mode=False,
    # BORÇ-4-bis (2 Haz 2026): max_iterations=3 — Lord direktifi
    # Sonsuz tool retry yok (Sahibinden CF block loop'a girdi 300s timeout)
    # Agno destekliyorsa max_iterations parametre adı; alternatif: tool_call_limit
)
# Walker LLM agent tool çağrı tavanı (BORÇ-4-bis)
MAX_TOOL_RETRY = 3  # max_iterations equivalence — Agno param degilse manuel guard


# ============================================================================
# BORÇ-4-bis (2 Haz 2026): crawlee_deep_crawl 4-katmanin her birinde
# short-content / CF / DataDome / Akamai signature check
# ============================================================================
_BLOCKED_SIGS_REGEX = r"(cf-ray|just a moment|cf_chl_|datadome|akamai|incapsula|_cf_bm|checking your browser)"

def _is_blocked_response(text: str, min_chars: int = 500) -> bool:
    """Crawlee/Crawl4AI/Camoufox dönüşünde CF/Akamai/DataDome interstitial detect.

    Args:
      text: katmanın döndürdüğü HTML/text
      min_chars: bu kadarın altı şüpheli (CF challenge sayfası ~58-1500 char)

    Returns:
      True: bloke edilmiş veya boş — bir sonraki katmana geç
      False: gerçek içerik — kullanılabilir
    """
    import re as _re_bb
    if not text or len(text) < min_chars:
        return True
    if _re_bb.search(_BLOCKED_SIGS_REGEX, text, _re_bb.IGNORECASE):
        return True
    return False


# ─────────────────────────────────────────
# GÖREV ÇALIŞTIRICI
# ─────────────────────────────────────────
def _run_walker(gorev: str) -> tuple[str, str | None]:
    _log(f"\n[WALKER] Yeni Görev: {gorev}")

    # load_from_memory (reranker'lı) ile geçmiş bağlamı al
    past_context_raw = load_from_memory(gorev)
    if "Hafızada ilgili kayıt bulunamadı" not in past_context_raw and "[WARN]" not in past_context_raw:
        _log("[WALKER] Geçmiş hafıza bulundu, bağlama ekleniyor.")
        enriched_gorev = gorev + f"\n\nGEÇMİŞ HAFIZA:\n{past_context_raw}"
    else:
        enriched_gorev = gorev

    response = walker_agent.run(enriched_gorev)

    text = ""
    if response and hasattr(response, "content"):
        text = response.content or ""
    else:
        text = str(response)

    text = re.sub(r'<\|tool_call\>.*?(?:<tool_call\|>|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'<\|tool_response\>.*?(?:<tool_response\|>|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'<\|[^|>]+\|?>', '', text)
    text = text.strip()

    if not text:
        text = "Görev tamamlandı Lordum, ancak metin raporu üretilemedi."

    # Raporu otomatik hafızaya kaydet
    mem_result = save_to_memory(f"GÖREV: {gorev[:200]}\nSONUÇ: {text[:3000]}")
    _log(f"[WALKER] Otomatik hafıza kaydı: {mem_result}")

    return text, None


# ─────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n  🔱 KUROSHIN WALKER SERVICE v3.0 AKTİF (Port {SERVICE_PORT})")
    print(f"  🧠 Agno Framework: {walker_agent.name}")
    print(f"  🛡️ Context Window: 128K Ready")
    print(f"  🔗 llama-server: {LLAMA_BASE_URL}")
    print(f"  💾 ChromaDB: {CHROMA_DATA_DIR}\n")
    yield


app = FastAPI(lifespan=lifespan)


class TaskRequest(BaseModel):
    task: str


@app.get("/health")
def health():
    return {"status": "ready", "version": "3.0"}


@app.get("/status")
def status():
    return {
        "status": "ready",
        "version": "3.0",
        "framework": "agno",
        "model": LLAMA_MODEL,
        "memory_ok": _MEMORY_OK,
    }


@app.post("/task")
def run_task(req: TaskRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Görev boş olamaz.")
    t0 = time.time()
    try:
        result, _ = _run_walker(req.task)
        return {
            "result": result,
            "elapsed": round(time.time() - t0, 1),
            "task": req.task[:100],
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {
            "result": f"[HATA] Walker hatası: {e}",
            "elapsed": round(time.time() - t0, 1),
            "task": req.task[:100],
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=SERVICE_PORT, loop="asyncio", log_level="warning")
