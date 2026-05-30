# Kuroshin OS — Mimari Belge v11.0.0
**Son Güncelleme:** 29 Mayıs 2026 — OTONOMİ-MAX Dalga 1 (KILIÇ-KALKAN v4 + Inquisitor Konsolide)

Yeni bir geliştirici veya Claude instance'ı bu belgeyi okuyarak sistemi 1 saatte anlayabilmelidir.

---

## Donanım Kısıtları

| Kaynak | Değer | Not |
|--------|-------|-----|
| CPU | Intel Core i7-12650H (12. Nesil, 10 çekirdek) | Host işlemci |
| RAM | 32GB DDR5-4800 Dual Channel (~76 GB/s) | MoE expert offload için kritik |
| GPU | RTX 4060 Laptop 8GB VRAM (140W max TGP) | Max 86°C — kritik eşik |
| SSD | Samsung NVMe PM9A1 1TB (~7000 MB/s) | Toplam depolama |
| Disk Doluluğu | ~12GB kullanımda | Temizlik sonrası (18 Mayıs 2026), RotatingFileHandler + disk_cleanup.sh |
| WSL | Ubuntu 22.04 (`-d Ubuntu-22.04`) | Tüm servisler WSL içinde |
| Windows | Python 3.x + Node.js | Dashboard + Agent Bridge |

---

## Port Haritası

| Port | Servis | Dosya | Durum |
|------|--------|-------|-------|
| 8080 | llama-server (Huihui-35B IQ4_XS, MoE) | `engines/llama.cpp/build/bin/llama-server` | ✅ Her zaman ayakta |
| 8100 | ChromaDB | `scripts/start_chromadb.sh` | ⚠️ Bat [1] ile başlar |
| 9002 | Walker Agent | `scripts/start_walker.sh` | ⚠️ Bat [1] ile başlar |
| 9003 | BGE Reranker | `scripts/start_reranker.sh` | ⚠️ Bat [1] ile başlar |
| 9004 | Ajan Konseyi | `scripts/start_council.sh` | ⚠️ Bat [1] ile başlar |
| **8201** | **Chancellor Internal Tool Server** | `agents/kuroshin_chancellor.py` (F5-01 thread) | ⚠️ **Bat [1] veya Bat [2] (restart)** |
| 3005 | Agent Bridge (Node, Windows) | `scripts/agent_bridge.js` | ⚠️ Bat [1] ile başlar |
| 3006 | Crawlee Bridge (Node) | `tools/crawlee_bridge.js` | ⚠️ Bat [1] ile başlar |
| 8091 | Nuclear Search MCP | `mcp_servers/search_server/kuroshin_engine.py` | ⚠️ Bat [1] ile başlar |
| 8888 | Dashboard | `src/dashboard/kuroshin_dashboard.py` | ⚠️ Bat [1] ile başlar |
| 6000 | LiteLLM Proxy | `venv/bin/uvicorn litellm...` | ❌ Boot'ta crash eder, görmezden gel |
| 6001 | LitServe | `src/serving/kuroshin_litserve.py` | ❌ Pasif |

---

## Servis Ağacı ve Başlatma Sırası

```
[0/6] Zombi temizliği
      pkill: llama-server, litellm, walker, council, reranker, chancellor,
             hype_scanner, global_scout, vram_guardian, pipeline_trigger,
             research_harvester, telegram_bridge, auto_integrator
      rm -f: /tmp/kuroshin_*.pid, /tmp/kuroshin_*.lock

[1/6] llama-server (active_model.json'dan dinamik — dense veya MoE)
      → curl /health polling max 120s

[2/6] LiteLLM + ChromaDB + Nuclear Search
      → LiteLLM curl polling max 60s (HTTP 200|401)
      → ChromaDB curl polling max 30s (/api/v2/heartbeat)

[3/6] Ajanlar
      Agent Bridge (Node, Windows)
      BGE Reranker (port 9003)
      Walker Agent (port 9002)
      Ajan Konseyi (port 9004)
      Kuroshin Şansölye (Telegram bot)
      LitServe
      VRAM Guardian
      Pipeline Daemon
      → Konsey+Reranker curl polling max 45s

[4/6] Otonom Sistemler
      Hype Scanner (daemon)
      Küresel Keşif (daemon)
      Auto Integrator

[5/6] Gauntlet Sağlık Testi
      scripts/kuroshin_health_check.sh
      scripts/boot_gauntlet_notify.sh → Telegram'a sonuç

[6/6] Dashboard + MCP + TUI
      kuroshin_dashboard.py
      mcp_toggle.py true → ~/.claude.json mcpServers'a Kuroshin sunucularını ekler
      <!-- NOT: Bu sadece orijinal Claude Code içindir. OpenClaude .mcp.json'dan okur. -->
      OpenClaude TUI (C:\Kuroshin\openclaude-main\openclaude-main\ dizininden başlar)
```

---

## Bileşen Açıklamaları

## Anlık Servis Durumu (23 Mayıs 2026 — v10.7.0)

| Bileşen | Durum | Not |
|---------|-------|-----|
| llama-server (8080) | ✅ AKTİF | Huihui-35B MoE IQ4_XS — 16K ctx, 20-21 tok/s |
| chancellor.py + :8201 | ✅ AKTİF | Telegram bot — **24 araç**, KILIC-KALKAN v3, Think Chain TK-01~09, F5-01 internal tool server :8201 (**setsid ile başlatılmalı**) |
| MCP sunucuları (stdio) | ✅ AKTİF | search, echo, bridge, walker, council, deerflow |
| hype_scanner.py | ✅ AKTİF | 09:00/21:00 tarama, daemon |
| global_scout.py | ✅ AKTİF | 20:00 dünya kaynak taraması, daemon |
| idle_loop.py | ✅ AKTİF | OODA probe her 2 saatte, otonom döngüler, next_wakeup.json fork (F5-05) |
| dream_engine.py | ✅ AKTİF | Gece 00:00'da aktifleşir |
| ChromaDB (8100) | ✅ AKTİF | Windows Start-Process WSL ile başlatılır |
| Walker HTTP (9002) | ✅ AKTİF | uvicorn, setsid |
| BGE Reranker (9003) | ✅ AKTİF | CUDA fp16 |
| Ajan Konseyi (9004) | ✅ AKTİF | uvicorn |
| Nuclear Search (8091) | ✅ AKTİF | Flask, Windows Start-Process WSL |
| Agent Bridge (3005) | ✅ AKTİF | Node.js, Windows process |
| LiteLLM (6000) | ❌ KAPALI | Boot'ta crash eder, görmezden gel |
| LitServe (6001) | ❌ KAPALI | Pasif |

> **KRİTİK NOT — WSL Süreç Yönetimi:**
> - ChromaDB ve Nuclear Search: **Windows `Start-Process wsl`** gerekir (`wsl -e bash -c "... &"` çalışmıyor)
> - Walker/Reranker/Council: `setsid bash start_*.sh` çalışır
> - **Chancellor (`agents/kuroshin_chancellor.py`)**: `setsid python3 chancellor.py &` zorunlu — `nohup/&` yetmez, bash oturumu kapanınca SIGHUP alır ve ölür
> - Bat [5] = tüm sistemi öldür | Bat [1] = tüm sistemi başlat (Chancellor dahil, 8201 beklenir)

---
- DOOM test: tüm servisler tam güç doğrulandı (ajan, 2026-05-23)

### Model Sistemi (`scripts/switch_model.py` + `memory/active_model.json`)
Tek merkezli model yönetimi — tüm servisler bu dosyadan okur.

- **Model kataloğu:** `MODEL_HINTS` + `MODEL_CONTEXT` — alias eşleştirme, context boyutu
- **MoE tespiti:** `_is_moe()` — isimde `a3b`, `-ax`, `moe` varsa MoE modu
- **Dense:** `--spec-type ngram-cache --draft-max 16` (speculative decoding)
- **MoE (Qwen3.6-35B-A3B):** `-ot "exps=CPU"` (expert'ler RAM'e, attention GPU'da)
- **Aktif model:** Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated IQ4_XS (18.7GB, 16K ctx, 20-21 tok/s)
- `start_llama.sh` ve 7 servis dosyası `active_model.json`'dan dinamik okur

### Otonom Ajan Sistemi (`scripts/kuroshin_autonomous.py` + yardımcılar)
FAZ 1-6 tamamlandı (22 Mayıs 2026). OODA döngüsü: Uyan → Karar Ver → Görev Çalıştır → Değerlendir → Güncelle → Planla → Uyu.
**HITL fix (23 Mayıs 2026):** HITL bloke sonrası `uyku_zamanla(30)` çağrılır — sistem 30dk sonra onay kontrolü için uyanır.

- **`scripts/kuroshin_autonomous.py`** — Ana ajan döngüsü (`KuroshinAjan` sınıfı, max 3 görev/oturum)
- **`scripts/kuroshin_goals.py`** — goals.json / tasks.json / task_context.json CRUD + döngü kırıcı + kalite kontrolü
- **`scripts/kuroshin_telegram_ajan.py`** — Telegram bildirim katmanı (start/progress/complete/blocked/daily_summary)
- **`scripts/kuroshin_md_agent.py`** — MD öz-güncelleme (todo_tamamla, bolume_ekle, yedek, ARCHITECTURE onay)
- **`memory/goals.json`** — Hedef deposu
- **`memory/tasks.json`** — Görev deposu (adım bazlı, md_guncelle dahili komut dahil)
- **`memory/task_context.json`** — Yarım görev bağlamı (crash-safe devam)
- **`memory/gorev_gecmisi.json`** — Son 5 görev geçmişi (döngü kırıcı)
- **`memory/next_wakeup.json`** — idle_loop.py için uyanış zamanı / zorla tetikleyici
- **`memory/reflections/`** — Görev sonrası model yansıma dosyaları
- **İç port 8201** — Chancellor internal tool server (autonomous → run_tool köprüsü)

### Think Chain Sistemi — TK-01~09 (`agents/kuroshin_chancellor.py`)
Modelin `<think>` bloğunu izler, yönlendirir ve kalitesini ölçer (23 Mayıs 2026).

| TK | Fonksiyon | Açıklama |
|----|-----------|----------|
| TK-01 | Logger | `logs/think_chain/YYYY-MM-DD.jsonl` — `think_turn`+`main` type |
| TK-02 | Steering | SYSTEM_PROMPT → `[NİYET][STRATEJİ][GÜVENLİK][RAFİNE]` 4 adım, Türkçe zorlama |
| TK-03 | Scorer | `_score_think()` — 4 adım(40p)+Türkçe(20p)+uzunluk(20p)+araç(20p) |
| TK-04 | Grounding | `_get_grounding_context()` — port/ChromaDB/aktif görev → think_turn'e enjekte |
| TK-05 | Audit | `logs/audits/YYYY-MM-DD.jsonl` — SHA256 + hash zinciri |
| TK-06 | FaultDetect | `_detect_think_faults()` — kısa think/eksik adım/araç döngüsü tespiti |
| TK-07 | ÇiftKontrol | Kritik komutlarda temp=0.7 ile ikinci görüş |
| TK-08 | DryRun | `system_command`+`write_file` `dry_run=True` simülasyon modu |
| TK-09 | Inquisitor | `test_suite_think.json` 8/8 %100 PASS |

---

### Kuroshin Şansölye (`agents/kuroshin_chancellor.py`)
Telegram botu — kullanıcının aktif modelle konuştuğu tek kapı.

- **Polling:** `getUpdates` long-polling (timeout=20s), exponential backoff
- **Mesaj işleme:** `ThreadPoolExecutor(max_workers=4)` — Qwen3'ün 120s timeout'u ana döngüyü bloklamaz
- **Lock:** `/tmp/kuroshin_chancellor.pid` O_EXCL atomik — tek instance garantisi
- **Araçlar (24):** `walker_research` · `web_search` · `system_command` · `memory_query` · `write_file` · `read_file` · `open_url` · `youtube_play` · `model_switch` · `pdf_reader` · `memory_manage` · `chroma_search` · `memory_integrity_scan` · `self_update` · `reminder` · `internet_status` · `system_info` · `reddit_read` · `reddit_tool` · `github` · `gemini` · `aktivite_gunluk` · `goal_manage` · `task_status`
- **write_file Desktop:** Agent Bridge safePath bypass → Python `Path.write_text()` direkt
- **Selamlama enforcer (v8.6.5):** `_strip_think()` → Lordım→Lordum typo fix; pipeline: boş/eksik selamlama → "⚔️ Lordum, " auto-prepend + log
- **XML sızıntı temizleyici (v8.6.9):** `_RESPONSE_LEAK_PATTERNS` — `<tool_call>{...}</tool_call>` ve `<function_call>` blokları strip edilir; agresif `|$` kullanılmaz (içerik kaybı önlenir)
- **Round 4 forced text (v8.6.9):** Son araç roundunda `"Düz Türkçe metin yaz, XML yazma"` talimatıyla çağrı yapılır — model `<tool_call>` XML üretimini bırakır
- **MİMİC Araçları (v8.8-9.3):** `reddit_read` (auth-free JSON), `reddit_tool` (PRAW — yorum/post/karma, 10dk rate limit, ban koruma; API credentials bekliyor), `github` (PyGitHub — push öncesi Telegram inline keyboard onayı; git timeout 60s + GIT_OPTIONAL_LOCKS=0; uçtan uca doğrulandı commit `db285dc`), `gemini` (google.genai `gemini-2.0-flash` — sor/tartis/karsilastir; 429/404 graceful hata), `aktivite_gunluk` (listele/ozet/kaydet — `logs/aktivite/YYYY-MM-DD.md`)
- **`scripts/trigger_push.py`:** Model bypass push tetikleyici — pending state `/tmp/kuroshin_pending_push.json`'a yazar, `github_push_onayla` callback gönderir, chancellor yakalar ve push'u gerçekleştirir.
- **Aktivite günlüğü (v8.9):** `aktivite_kaydet(eylem, detay, kategori)` — 6 noktada otomatik çağrılır (gemini, reddit, github push, github issue, run_tool, walker). Gece 22:00 `_aktivite_gunluk_ozet()` Telegram özeti.
- **Kuroshin.bat dinamik header (v8.9):** `:MAIN_MENU` başında PowerShell ile `active_model.json` okunur → `MODEL_KISA` değişkeni → `Beyin: !MODEL_KISA! | OODA Probe | KADEMELI UYANIS` header her açılışta güncellenir.
- **Log:** `RotatingFileHandler` 5MB/3 backup → `/mnt/c/Kuroshin/logs/chancellor.log`

### Walker Agent (`agents/kuroshin_walker_service.py`, port 9002)
Web araştırma + RAG + ChromaDB hafıza.

- ChromaDB'ye belge ekler/sorgular
- BGE Reranker ile sonuçları kalite sıralar (top-10 → top-3)
- Web erişim zinciri (katmanlı fallback):
  - `web_reader_tool`: Crawl4AI → Camoufox hayalet Firefox
  - `crawlee_deep_crawl`: Crawlee Bridge (port 3006, simple/playwright/stealth) → Crawl4AI → Camoufox

### Ajan Konseyi (`agents/kuroshin_council_service.py`, port 9004)
Smolagents çerçevesi — iki uzman ajan:

- **Teknisyen:** `read_file`, `write_file`, `run_shell`
- **Gözcü:** `DuckDuckGoSearchTool` — GitHub/HF trend takibi

### BGE Reranker (`scripts/kuroshin_reranker_service.py`, port 9003)
`BAAI/bge-reranker-v2-m3` — ChromaDB'den gelen 10 sonucu 3'e süzer.

### Hype Scanner (`scripts/hype_scanner.py`)
Sabah 09:00 + Akşam 21:00 otomatik tarama:
GitHub Trending + HuggingFace Papers + HF GGUF → Qwen3 analizi → Telegram raporu.

- Catchup: son taramadan bu yana >12 saat geçtiyse otomatik tetikler
- VRAM tahmini: `estimate_vram()` ile GGUF dosya adından quant+param parse

### Küresel Keşif (`scripts/global_scout.py`)
Her gün 20:00 dünya kaynaklarını tarar:
Habr RSS · Gitee API · arXiv · HF Datasets · HackerNews · Papers with Code · Exploit-DB

- IP Skoru: kaynak güvenilirlik ağırlığı × keyword skoru
- Çeviri: PeCa 1B → fallback deep-translator

### DeerFlow MCP v2.0 (`mcp_servers/deerflow_server/kuroshin_deerflow_mcp.py`)
Bağımsız araştırma MCP sunucusu — subprocess bağımlılığı yok.

- **`deerflow_research`:** DuckDuckGo → Crawl4AI → Crawlee fallback → Qwen3 analizi → ChromaDB upsert
  - `sources` parametresi: 1-3 kaynak (varsayılan 2)
  - Hava durumu sorguları desteklenir
- **`walker_deep_research`:** Walker Agent (port 9002) üzerinden kapsamlı araştırma

### Auto Integrator (`scripts/auto_integrator.py`)
Walker/Scout raporlarını ChromaDB'ye entegre eder, kalite filtreler.

### src/ Modül Katmanı (Entegrasyon Yolu)

Merkezi Python modülleri — aktif servisler henüz import etmiyor, ileride orkestrasyon için:

- **`src/core/llm_client.py`** — `KuroshinLLMClient`: LiteLLM üzerinden merkezi LLM bağlantısı
- **`src/memory/kuroshin_smart_memory.py`** — `KuroshinSmartMemory`: ChromaDB fact extraction (Qwen3)
- **`src/serving/kuroshin_litai_router.py`** — Async LiteLLM→llama-server fallback router
- **`src/serving/kuroshin_litserve.py`** — FastAPI proxy (port 6001), llama-server 8080 önünde
- **`src/orchestration/coordinator.py`** — `KuroshinCoordinator`: DeerFlow + LLM + Memory pipeline
- **`src/agents/deerflow/deerflow_core.py`** — DeerFlow v2.1 standalone CLI ajanı

---

## Veri Akışı

```
Telegram mesajı
    ↓
kuroshin_chancellor.py (polling)
    ↓ ThreadPoolExecutor
process_message() → Qwen3 (llama-server:8080)
    ↓ tool_call
run_tool() → [walker_research | web_search | system_command | ...]
    ↓
Walker Agent (9002) → ChromaDB (8100) ← BGE Reranker (9003)
                    → DuckDuckGo / Camoufox
    ↓
Yanıt → Telegram
```

```
Otonom döngü (cronjob/daemon):
hype_scanner / global_scout
    ↓ kaynak tarama
Qwen3 analizi
    ↓
auto_integrator → ChromaDB
    ↓
Telegram raporu
```

---

## Otonom Güç Haritası (v9.4.0)

### 24 Araç — Kategori Tablosu

| Kategori | Araçlar | Güç Seviyesi |
|----------|---------|-------------|
| Araştırma | `walker_research`, `web_search`, `pdf_reader`, `chroma_search`, `memory_query` | Derin web + RAG + PDF |
| Hafıza | `memory_manage`, `memory_integrity_scan`, `chroma_search` | ChromaDB CRUD + güvenlik tarama |
| Sistem | `system_command`, `write_file`, `read_file`, `system_info`, `internet_status` | WSL shell + dosya sistemi |
| Sosyal/Dış | `github`, `gemini`, `reddit_read`, `reddit_tool`, `open_url`, `youtube_play` | GitHub push, Gemini diyaloğu, Reddit |
| Meta | `model_switch`, `self_update`, `reminder`, `aktivite_gunluk` | Beyin değişimi, ruh sıfırlama, hatırlatıcı |
| Otonom Ajan | `goal_manage`, `task_status` | Hedef/görev CRUD, otonom döngü yönetimi |

### 9 Otonom Döngü

| Döngü | Tetik | Çıktı |
|-------|-------|-------|
| OODA Probe | Her 2 saat | Araştırma + `[👍][👎][🔍]` feedback |
| Hype Scanner | 09:00 / 21:00 | GitHub Trending + HF Papers raporu |
| Küresel Keşif | 20:00 | Habr/arXiv/HN/Gitee tarama |
| Dream Engine | 00:00 | Rüya sentezi → ChromaDB + log |
| Günlük araştırma | 10:00 | 2 konu → walker/web_search → ChromaDB |
| Aktivite özeti | 22:00 | `logs/aktivite/YYYY-MM-DD.md` → Telegram |
| Öz-yansıma | 23:00 | Deneyim günlüğü → Qwen3 meta-yorum |
| ChromaDB haftalık | Pazar 23:00 | Hafıza özeti → Telegram |
| Canlılık araştırması | Her 7 gün | Schema keşif → `logs/schema_kesfler/` |

### Araç Zincirleme — Çok Adımlı Görev Akışı

```
Görev: "X konusunu araştır, Gemini'ye sor, GitHub'a commit et"
    ↓
[1] internet_status → bağlantı doğrula
    ↓
[2] walker_research(X) → ChromaDB'ye kaydet
    ↓
[3] gemini(sor, X_özeti) → dış perspektif al
    ↓
[4] write_file(rapor.md) → sonuçları yaz
    ↓
[5] github(push) → Telegram onay → commit
    ↓
[6] aktivite_gunluk(kaydet) → günlüğe ekle
```

Model bu zinciri tek `process_message()` döngüsü içinde, max 4 araç roundunda yürütür.
Round limiti aşılırsa model `forced_text` moduna geçer ve özet yanıt üretir.

---

## Güvenlik & Sırlar

Tüm sırlar `C:\Kuroshin\.env` dosyasında — `.gitignore`'da `.*` ile hariç tutulmuş.

```
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
BRIDGE_SECRET=kuroshin-bridge-2026
LITELLM_MASTER_KEY=kuroshin-secret
OPENAI_API_KEY=kuroshin-secret
WP_TOKEN=...
GEMINI_API_KEY=...          # google.genai gemini-2.0-flash
GITHUB_TOKEN=...            # KuroShinHQ repo push (17 Haz 2026)
REDDIT_CLIENT_ID=...        # PRAW — karma biriktirince doldur
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=...
```

Her Python dosyası başında:
```python
from dotenv import load_dotenv
load_dotenv(Path("/mnt/c/Kuroshin/.env"))
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
```

---

## Log Yapısı

```
/mnt/c/Kuroshin/logs/
├── chancellor.log           RotatingFileHandler 5MB/3 backup
├── hype_scanner.log         RotatingFileHandler 5MB/3 backup
├── global_scout.log         RotatingFileHandler 5MB/3 backup
├── llama-server.log         düz dosya (büyüyebilir)
├── litellm.log              düz dosya
├── agent_bridge.log         Node.js stdout
├── system.log               Kuroshin.bat olay kayıtları
├── disk_cleanup.log         günlük temizlik raporu
├── aktivite/                MİMİC aktivite günlükleri
│   └── YYYY-MM-DD.md        günlük eylem kaydı (aktivite_kaydet)
└── dreams/                  Dream Engine rüya kayıtları
    └── rüya_TARIH.txt
```

`scripts/disk_cleanup.sh` her gece 03:00'da çalışır:
- pip cache purge
- 10MB+ logları sıfırla
- HF cache `.incomplete` temizle
- Telegram'a disk durumu bildir

---

## MCP Sunucuları (Claude Code için)

<!-- ÖNEMLİ — İKİ FARKLI BAĞLAM:
  1. Orijinal Claude Code (`claude` komutu): MCP'ler KAPALI olmalı.
     Toggle mekanizması: scripts/mcp_toggle.py
       - false → 6 sunucuyu ~/.claude.json mcpServers'dan kaldırır, mcpServersKuroshinBackup'a saklar
       - true  → backup'tan geri yükler, mcpServers'a ekler
     NOT: Claude Code'da "disabled: true" alanı dikkate ALINMIYOR — girişleri tamamen kaldırmak gerekiyor.

  2. OpenClaude TUI (Kuroshin.bat [1] Walker Modu): MCP'ler AKTİF.
     Config: C:\Kuroshin\openclaude-main\openclaude-main\.mcp.json (ve üst dizin .mcp.json)
     OpenClaude bu dosyayı kendi çalışma dizininden okur — ~/.claude.json'dan bağımsız.

  Kuroshin.bat akışı:
    [1] Walker başlar → mcp_toggle.py true  → mcpServers'a eklenir (orijinal Claude Code için)
    [5] Sistem Kapat  → mcp_toggle.py false → mcpServers'dan kaldırılır
    [7] Çıkış        → mcp_toggle.py false → mcpServers'dan kaldırılır
-->

`openclaude-main/.mcp.json` — OpenClaude TUI'nin kullandığı araçlar (orijinal Claude Code'dan bağımsız):

| MCP | Araç | Açıklama |
|-----|------|----------|
| `kuroshin-echo` | `echo` | Bağlantı testi |
| `kuroshin-search` | `web_search`, `fetch_page`, `fetch_page_deep`, `fetch_page_stealth` | Web erişimi |
| `kuroshin-bridge` | `list_dir`, `read_file`, `write_file`, `bridge_status` | Sistem araçları |
| `kuroshin-walker` | `walker_task`, `walker_status` | RAG + web araştırma (Agno + ChromaDB) |
| `kuroshin-council` | `council_teknisyen`, `council_gozcu` | Ajan Konseyi (Smolagents) |
| `kuroshin-deerflow` | `deerflow_research`, `walker_deep_research` | Otonom araştırma motoru |

`scripts/mcp_toggle.py`: MCP'leri boot'ta aktif, shutdown'da devre dışı bırakır.
- `true`  → `~/.claude.json` `mcpServers`'a Kuroshin sunucularını geri yükler
- `false` → `mcpServers`'dan kaldırır, `mcpServersKuroshinBackup` key'inde saklar

---

---

## KILIC-KALKAN v3 — Güvenlik Sistemi (v9.0.0–v9.4.0)

`scripts/kuroshin_security.py` — Merkezi güvenlik modülü. **24 fonksiyon** (29 May 2026: +mcp_poison +representation_drift +semantic_chameleon), 3 entegrasyon noktası.

### Savunma Katmanları

| Katman | Fonksiyon | Açıklama |
|--------|-----------|----------|
| **Encoding Kalkanı** | `decode_and_rescan()` | Base64 → Morse → ROT13 → Homoglyph → Leet → decode + yeniden tara |
| | `purge_invisible_chars()` | ZWS/ZWNJ/ZWJ/WJ/LRM/RLM/BOM/VS temizliği (T2+T14) |
| | `detect_unicode_tag_smuggling()` | U+E0000-E007F Tags Block ASCII gizleme (T13) |
| **Crescendo** | `escalation_score()` | 5 mesaj penceresinde konu kayması skoru (0.0–1.0); 0.7+ → Telegram uyarısı |
| **Bellek Kalkanı** | `scan_chroma_documents()` | ChromaDB toplu injection + SHA256 hash doğrulama |
| | `verify_prompt_integrity()` | System prompt SHA256 kilidi (`memory/prompt_integrity.json`) |
| | `scan_output_encoding()` | Çıktıda Base64 ≥40 kar / Morse yoğunluğu / Unicode >%10 tespiti |
| **Ağ Saldırıları** | `sanitize_web_content()` | Web içeriği → purge → tags_block → decode_and_rescan pipeline |
| | `tag_unverified_content()` | Dış kaynak içerik sarmalama (`[UNVERIFIED_WEB:...]`) |
| **Kimlik/Akıl** | `monitor_think_drift()` | THINK bloğu semantik sapma tespiti (T27) |
| | `detect_reasoning_hijack()` | UDora tarzı trace insertion (ICML 2025, T42) |
| | `detect_mcfa()` | Memory Control Flow Attack (arXiv 2603.15125, T41) |
| | `detect_constraint_tightening()` | Constraint tersine argüman (arXiv 2604.05549, T46) |
| | `detect_adversarial_suffix()` | GCG suffix bypass (arXiv 2505.09602, T48) |
| | `detect_script_anomaly()` | Arkaik/nadir script tespiti (CJK Ext, Cuneiform, Hieroglyph, T7) |
| | `detect_logibreak()` | Binary/hex/sembolik gizleme (T8) |
| | `alignment_check()` | Plan↔eylem tutarlılık — LlamaFirewall yerel analog (T47) |
| **Sistem Güvenliği** | `formal_safety_check()` | 8 LTL değişmezi: shadow/mass_delete/pipe_exec/priv_esc/reverse_shell/mem_exfil/cred_exfil/outbound_tunnel (T35) |
| | `sign_agent_payload()` / `verify_agent_payload()` | HMAC-SHA256 servisler arası imzalama + 30s replay koruması (T23) |
| | `extract_attacker_fingerprint()` | 6 saldırı tipi parmak izi: jailbreak/authority_spoof/encoding/persona/crescendo/memory_poison (T20) |
| | `generate_honeypot_response()` | Sahte ortam yanıtı — risk==HIGH + escalation>0.85 (T21) |
| | `calculate_asr()` | Gray Swan ASR metriği (T52) |

### Chancellor Entegrasyon Noktaları

| Nokta | Güvenlik Kontrolü |
|-------|-------------------|
| `_strip_think()` | injection scan + monitor_think_drift + detect_reasoning_hijack + alignment_check |
| `_get_chroma_context()` | scan_chroma_documents (hash) + detect_mcfa her döküman için |
| `process_message()` başı | escalation_score + detect_constraint_tightening; `_CURRENT_USER_MSG` global set |
| `_save_to_chroma()` | scan_for_injection yazma öncesi |
| `system_command` handler | check_command + formal_safety_check (ikinci semantik katman) |
| `send_msg` öncesi | scan_output_encoding |

### Supply Chain Savunması

- `_BLOCKED_EXACT`: `pip install git+http://`, `--index-url http://`, `--extra-index-url http://`
- `_BLOCKED_REGEX`: `pip install git+https://` — non-GitHub kaynaklar engellendi
- `_WARN_PATTERNS`: `pip install` / `pip uninstall` loglanıyor (izin veriliyor)

---

## Iron Inquisitor v5 — Test Sistemi (v10.7.0)

`scripts/iron_inquisitor/inquisitor_v5.py` — **61 güvenlik testi + 49 full suite testi, %100 PASS** (23 Mayıs 2026)

**Full Suite (`test_suite_full_v2.json`):** 49/49 %100 — 70.5/70.5 puan (crawlee-01/02/03/sync-01 timeout 300s)

| Test Suite | Dosya | Test | Sonuç |
|------------|-------|------|-------|
| Temel güvenlik (KILIC-KALKAN v1) | (inquisitor_v5 dahili) | 14 | ✅ %100 |
| KILIC-KALKAN v2 genişleme | `test_suite_security_v2.json` | 32 | ✅ %100 |
| Red Team v3 simülasyonu | `test_suite_security_v3.json` | 4 | ✅ %100 |
| KILIC-KALKAN v3 FAZ 1+2+3 | `test_suite_security_v4.json` | 25 | ✅ %100 |
| **TOPLAM** | | **61** | **✅ %100** |

**v4 FAZ dağılımı (test_suite_security_v4.json):**
- FAZ 1 (7 test): tags_block, invisible_purge, minja injection, XPIA sanitize
- FAZ 2 (9 test): mcfa, constraint_tighten, think_drift, reasoning_hijack, script_anomaly, logibreak
- FAZ 3 (9 test): invariant_check, hmac_verify, fingerprint, alignment, asr_report

**Check tipleri (inquisitor_v5.py):**
`port_check` · `security_check` · `encoding_check` · `escalation` · `chroma_poison` · `output_encoding`
· `web_sanitize` · `tags_block` · `invisible_purge` · `mcfa` · `constraint_tighten` · `think_drift`
· `reasoning_hijack` · `invariant_check` · `hmac_verify` · `fingerprint` · `alignment` · `asr_report`

**ASR otomatik raporu:** `expect_blocked=True` testler otomatik saldırı testi sayılır, ASR hesaplanır, Telegram raporuna `🔐 ASR: 0.0% | engellendi 15/15` satırı eklenir.

- **OpenClaude bağımlılığı YOK** — MCP sunucularını direkt stdio JSON-RPC ile çağırır
- **Self-healing:** Bridge (3005), Walker (9002), llama-server (8080) otomatik başlatılır
- **Seçici Çalıştırma:**
  - `--only <id1> <id2>` — sadece belirtilen test ID'leri
  - `--category <cat>` — kategoriye göre filtre
  - `--skip-passed` — son rapordaki PASS testleri atla
  - `--no-telegram` — yerel test modunda Telegram sessiz
- **WSL içinden servis başlatma:**
  - Bridge → `/mnt/c/Windows/System32/cmd.exe /c "... node agent_bridge.js"`
  - Walker → `/bin/bash -c "source venv && nohup uvicorn ..."`
  - llama-server → `/bin/bash /mnt/c/Kuroshin/scripts/start_llama.sh`
  - WSL içinden `wsl` komutu çağrılamaz — bu yollar kullanılmalı

**Tam suite çalıştırma:**
```bash
wsl -d Ubuntu-22.04 --exec /bin/bash -c "source /root/kuroshin/venv/bin/activate && python3 -u /mnt/c/Kuroshin/scripts/iron_inquisitor/inquisitor_v5.py"
```

**Sadece başarısızları yeniden çalıştırma:**
```bash
wsl -d Ubuntu-22.04 --exec /bin/bash -c "source /root/kuroshin/venv/bin/activate && python3 -u /mnt/c/Kuroshin/scripts/iron_inquisitor/inquisitor_v5.py --skip-passed"
```

**Kuroshin.bat → [9]:** Eval Feedback Loop GUI menüsü (test-only / auto-apply / tek döngü)

---

## Kritik Notlar

1. **`/root/kuroshin/` KULLANMA** — Tüm path'ler `/mnt/c/Kuroshin/` olmalı. `kuroshin_user` kullanıcısı `/root/` erişemez.
2. **Agent Bridge `safePath()`** — Bridge yalnızca `C:\Kuroshin\` altına yazar. Desktop için chancellor'da Python `Path.write_text()` bypass kullanılıyor.
3. **LLM `system_command`** — Sistem prompt'ta açıkça "printf/echo kullanma, write_file kullan" kuralı var. Yoksa model shell komutlarıyla dosya yazmaya çalışır.
4. **O_EXCL lock** — `fcntl.flock()` WSL cross-session'da çalışmıyor. Chancellor ve hype_scanner `O_EXCL` flag'li open() kullanıyor.
5. **LiteLLM auth** — `/health` endpoint 401 döner (key gerektirir). Boot polling `HTTP 200|401` ikisini de PASS sayar.
6. **Konsey `/health`** — FastAPI `/health`, `/status` değil. Health check buna göre yapılandırıldı.
7. **WSL içinden `wsl` çağrılamaz** — Servis başlatırken `wsl` binary'si mevcut değil. `/bin/bash` veya `/mnt/c/Windows/System32/cmd.exe` tam yolu gerekli.
