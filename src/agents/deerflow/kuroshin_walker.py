"""
Kuroshin Walker v1 — Agno Orkestratör
======================================
Lord Kuroshin_user'nun emriyle inşa edildi.
Yerel Gemma 4 (LiteLLM :4000) üzerinde çalışan otonom web gözcüsü.

FAZ-2: Temel bağlantı + yaşam testi          ✅
FAZ-3: ChromaDB hafıza + Crawl4AI web okuma  ✅
FAZ-4: Performans opt. + hafıza yazma + döngü ← AKTIF
"""

import asyncio
import time
import uuid
import chromadb
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from crawl4ai import AsyncWebCrawler

# ─────────────────────────────────────────
# SABITLER
# ─────────────────────────────────────────
CRAWL_CHAR_LIMIT = 4000       # FAZ-4: 8000 → 4000 (Gemma4 thinking süresi ~2-4x azalır)
MAX_OUTPUT_TOKENS = 768       # Özet çıktı limiti — tool result + özet için yeterli alan
LITELLM_BASE_URL  = "http://127.0.0.1:6000/v1"  # v2.2: port 4000 → 6000
LLAMA_BASE_URL    = "http://127.0.0.1:8080/v1"  # LiteLLM çökerse fallback

# ─────────────────────────────────────────
# MODEL: LiteLLM → Qwen3-8B Abliterated
# ─────────────────────────────────────────
qwen3 = OpenAILike(
    id="qwen3-abliterated",
    api_key="kuroshin-secret",
    base_url=LITELLM_BASE_URL,
    timeout=120,
    max_tokens=MAX_OUTPUT_TOKENS,
)

# ─────────────────────────────────────────
# HAFIZA: ChromaDB HTTP (:8100)
# ─────────────────────────────────────────
try:
    chroma_client = chromadb.HttpClient(host="127.0.0.1", port=8100)
    memory_col = chroma_client.get_or_create_collection("kuroshin_memory")
    _MEMORY_OK = True
except Exception as e:
    print(f"  [WARN] ChromaDB bağlantısı kurulamadı: {e}")
    memory_col = None
    _MEMORY_OK = False


# ─────────────────────────────────────────
# ARAÇ 1: Web Okuyucu (Crawl4AI)
# ─────────────────────────────────────────
async def _fetch(url: str) -> str:
    from crawl4ai import CrawlerRunConfig
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    # PruningContentFilter: menü/nav gürültüsünü eler, asıl paragrafları tutar
    run_cfg = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.45,
                threshold_type="fixed",
                min_word_threshold=5,
            )
        ),
        exclude_external_links=True,
        remove_overlay_elements=True,
        word_count_threshold=10,
        page_timeout=15000,
        wait_until="domcontentloaded",
    )
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)
        if result.success:
            content = ""
            # fit_markdown = PruningFilter uygulanmış, en temiz versiyon
            if hasattr(result, "markdown_v2") and result.markdown_v2:
                content = (
                    getattr(result.markdown_v2, "fit_markdown", None)
                    or getattr(result.markdown_v2, "raw_markdown", None)
                    or ""
                )
            if not content:
                content = result.markdown or ""
            # Son kontrol: gerçekten içerik var mı?
            if len(content.strip()) < 100:
                # CSS selector olmadan tekrar dene (dinamik sayfa fallback)
                result2 = await crawler.arun(url=url)
                content2 = result2.markdown or "" if result2.success else ""
                if len(content2) > len(content):
                    content = content2
            print(f"  [CRAWL] {len(content)} kar → {CRAWL_CHAR_LIMIT} ile kırpıldı.")
            return content[:CRAWL_CHAR_LIMIT]
        return f"HATA: {url} okunamadı — {getattr(result, 'error_message', 'bilinmiyor')}"


def web_reader_tool(url: str) -> str:
    """
    Bir web sitesinin güncel içeriğini okumak için kullan.
    Parametre: url — tam adres (https:// ile başlamalı).
    Döndürür: Sayfanın kırpılmış metin içeriği.
    """
    print(f"\n  [WEB] Hedef: {url}")
    t0 = time.time()
    result = asyncio.run(_fetch(url))
    print(f"  [WEB] Tamamlandı ({time.time()-t0:.1f}sn)")
    return result


# ─────────────────────────────────────────
# ARAÇ 2: Hafıza Yazıcı (ChromaDB)
# ─────────────────────────────────────────
def save_to_memory(bilgi: str) -> str:
    """
    Elde edilen kritik bilgileri ve özetleri ChromaDB vektör hafızasına kalıcı olarak yazar.
    Parametre: bilgi — kaydedilecek özet veya bilgi metni.
    ÖNEMLI: Bu aracı YALNIZCA BİR KEZ çağır. Aynı bilgiyi tekrar kaydetme.
    """
    if not _MEMORY_OK or memory_col is None:
        return "[WARN] ChromaDB bağlı değil, hafızaya yazılamadı."
    try:
        doc_id = f"walker_{uuid.uuid4().hex[:8]}"
        memory_col.upsert(
            documents=[bilgi[:2000]],
            ids=[doc_id],
            metadatas=[{"source": "walker", "ts": str(int(time.time()))}],
        )
        count = memory_col.count()
        print(f"  [HAFIZA] Kaydedildi → id:{doc_id} | toplam kayıt:{count}")
        return f"Hafızaya kazındı. (id:{doc_id}, toplam:{count} kayıt)"
    except Exception as e:
        return f"[HATA] Hafıza yazma başarısız: {e}"


# ─────────────────────────────────────────
# ŞEF AGNO — Walker Orkestratör (FAZ-4)
# ─────────────────────────────────────────
walker_agent = Agent(
    model=qwen3,
    description=(
        "Sen Kuroshin İmparatorluğu'nun zeki ve otonom Web Gözcüsü ve Orkestratörüsün. "
        "Lord Kuroshin_user'ya sadık, Türkçe konuşan, hedefe odaklı bir ajansın.\n\n"
        "KURALLAR:\n"
        "1. Web araştırması gerektiren görevlerde 'web_reader_tool' aracını kullan.\n"
        "2. Öğrendiğin yeni ve önemli bilgileri HER ZAMAN 'save_to_memory' aracıyla hafızaya kaydet.\n"
        "3. Gereksiz açıklama yapma. Kısa, net, Türkçe cevap ver.\n"
        "4. Özetler en fazla 3 madde olsun."
    ),
    tools=[web_reader_tool, save_to_memory],
    markdown=True,
    debug_mode=False,
)


# ─────────────────────────────────────────
# OTONOM AVLANMA DÖNGÜSÜ (FAZ-4)
# ─────────────────────────────────────────
def _print_banner():
    count = memory_col.count() if _MEMORY_OK and memory_col else "?"
    print("\n" + "=" * 62)
    print("  KUROSHIN WALKER v1 — OTONOM AVLANMA DÖNGÜSÜ")
    print("  Model   : Gemma4 via LiteLLM :4000")
    print("  Araçlar : web_reader_tool | save_to_memory")
    print(f"  Hafıza  : ChromaDB kuroshin_memory — {count} kayıt")
    print("=" * 62)
    print("  Komutlar: URL içeren herhangi bir görev")
    print("            'hafıza' → hafıza içeriğini listele")
    print("            'q' veya 'quit' → çıkış")
    print("=" * 62 + "\n")


def _show_memory():
    if not _MEMORY_OK or memory_col is None:
        print("  [WARN] ChromaDB bağlı değil.")
        return
    count = memory_col.count()
    print(f"\n  [HAFIZA] {count} kayıt mevcut:")
    if count == 0:
        print("  (boş)")
        return
    results = memory_col.get(limit=10)
    for i, (doc_id, doc) in enumerate(zip(results["ids"], results["documents"]), 1):
        preview = doc[:120].replace("\n", " ")
        print(f"  [{i}] {doc_id}: {preview}...")
    print()


def _url_in(text: str) -> str | None:
    """Komutta URL var mı? Varsa döndür."""
    for word in text.split():
        if word.startswith("http://") or word.startswith("https://"):
            return word
    return None


def _smart_task(gorev: str) -> tuple[str, bool]:
    """
    URL içeren görevlerde web içeriğini önceden çekip prompt'a gömer.
    Böylece Gemma4 tek çağrıda hem okur hem özetler — tool call overhead yok.
    URL yoksa görevi doğrudan ajana iletir.
    Döndürür: (prompt, url_onceden_cekildimi)
    """
    url = _url_in(gorev)
    if url:
        print(f"\n  [PRE-FETCH] URL tespit edildi: {url}")
        content = web_reader_tool(url)
        prompt = (
            f"{gorev}\n\n"
            f"Aşağıda '{url}' adresinden çekilen sayfa içeriği:\n\n"
            f"---\n{content}\n---\n\n"
            f"Bu içeriği analiz et, özetini yap ve 'save_to_memory' aracıyla hafızaya kaydet."
        )
        return prompt, True
    return gorev, False


def start_autonomous_loop():
    _print_banner()
    print("  Otonom avlanma döngüsü aktif. Lord Kuroshin_user'nun emirleri bekleniyor...\n")

    while True:
        try:
            gorev = input("[LORD] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Sistem uyku moduna geçiyor...")
            break

        if not gorev:
            continue

        if gorev.lower() in ("q", "quit", "exit", "çıkış"):
            print("  Sistem uyku moduna geçiyor. Hafıza korundu.")
            break

        if gorev.lower() in ("hafıza", "memory", "hafiza"):
            _show_memory()
            continue

        print(f"\n  [GÖREV ALINDI] {gorev}")
        t0 = time.time()
        prompt, prefetched = _smart_task(gorev)
        # URL önceden çekildiyse web_reader_tool'u devre dışı bırak (çift fetch engeli)
        if prefetched:
            walker_agent.tools = [save_to_memory]
        else:
            walker_agent.tools = [web_reader_tool, save_to_memory]
        walker_agent.print_response(prompt, stream=True, show_reasoning=False)
        elapsed = time.time() - t0
        print(f"\n  [TAMAMLANDI] {elapsed:.1f}sn | hafıza: {memory_col.count() if _MEMORY_OK and memory_col else '?'} kayıt\n")


if __name__ == "__main__":
    start_autonomous_loop()
