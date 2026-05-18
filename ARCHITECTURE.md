# Kuroshin OS — Mimari Belge v8.6
**Son Güncelleme:** 18 Mayıs 2026

Yeni bir geliştirici veya Claude instance'ı bu belgeyi okuyarak sistemi 1 saatte anlayabilmelidir.

---

## Donanım Kısıtları

| Kaynak | Değer | Not |
|--------|-------|-----|
| CPU | Intel Core i7-12650H (12. Nesil) | Host işlemci |
| RAM | 32GB DDR4 | Toplam sistem belleği |
| GPU | RTX 4060 Laptop 8GB VRAM (140W) | Max 86°C — kritik eşik |
| SSD | 1TB NVMe | Toplam depolama |
| Disk Doluluğu | ~12GB kullanımda | Temizlik sonrası (18 Mayıs 2026), RotatingFileHandler + disk_cleanup.sh |
| WSL | Ubuntu 22.04 (`-d Ubuntu-22.04`) | Tüm servisler WSL içinde |
| Windows | Python 3.x + Node.js | Dashboard + Agent Bridge |

---

## Port Haritası

| Port | Servis | Dosya | Health Endpoint |
|------|--------|-------|-----------------|
| 8080 | llama-server (Qwen3-abliterated) | `engines/llama.cpp/build/bin/llama-server` | `GET /health` → `{"status":"ok"}` |
| 6000 | LiteLLM Proxy | `venv/bin/uvicorn litellm...` | `GET /health` → HTTP 200/401 |
| 6001 | LitServe | `src/serving/kuroshin_litserve.py` | — |
| 8100 | ChromaDB | `scripts/start_chromadb.sh` | `GET /api/v2/heartbeat` → `{"nanosecond heartbeat":...}` |
| 9002 | Walker Agent | `scripts/start_walker.sh` | `GET /health` |
| 9003 | BGE Reranker | `scripts/start_reranker.sh` | `GET /health` → `{"status":"ready"}` |
| 9004 | Ajan Konseyi | `scripts/start_council.sh` | `GET /health` → `{"status":"ready"}` |
| 3005 | Agent Bridge (Node) | `scripts/agent_bridge.js` | HTTP POST endpoint |
| 3006 | Crawlee Bridge (Node) | `tools/crawlee_bridge.js` | `GET /health` → `{"status":"ok"}` |
| 8091 | Nuclear Search MCP | `mcp_servers/search_server/kuroshin_engine.py` | — |
| 8888 | Dashboard | `src/dashboard/kuroshin_dashboard.py` | — |

---

## Servis Ağacı ve Başlatma Sırası

```
[0/6] Zombi temizliği
      pkill: llama-server, litellm, walker, council, reranker, chancellor,
             hype_scanner, global_scout, vram_guardian, pipeline_trigger,
             research_harvester, telegram_bridge, auto_integrator
      rm -f: /tmp/kuroshin_*.pid, /tmp/kuroshin_*.lock

[1/6] llama-server (Qwen3 128K)
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
      mcp_toggle.py → MCP'leri aktif et
      OpenClaude TUI
```

---

## Bileşen Açıklamaları

### Kuroshin Şansölye (`agents/kuroshin_chancellor.py`)
Telegram botu — kullanıcının Qwen3 ile konuştuğu tek kapı.

- **Polling:** `getUpdates` long-polling (timeout=20s), exponential backoff
- **Mesaj işleme:** `ThreadPoolExecutor(max_workers=4)` — Qwen3'ün 120s timeout'u ana döngüyü bloklamaz
- **Lock:** `/tmp/kuroshin_chancellor.pid` O_EXCL atomik — tek instance garantisi
- **Araçlar (8):** `walker_research` · `web_search` · `system_command` · `memory_query` · `write_file` · `read_file` · `open_url` · `youtube_play`
- **write_file Desktop:** Agent Bridge safePath bypass → Python `Path.write_text()` direkt
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

## Güvenlik & Sırlar

Tüm sırlar `C:\Kuroshin\.env` dosyasında — `.gitignore`'da `.*` ile hariç tutulmuş.

```
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
BRIDGE_SECRET=kuroshin-bridge-2026
LITELLM_MASTER_KEY=kuroshin-secret
OPENAI_API_KEY=kuroshin-secret
WP_TOKEN=...
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
├── chancellor.log       RotatingFileHandler 5MB/3 backup
├── hype_scanner.log     RotatingFileHandler 5MB/3 backup
├── global_scout.log     RotatingFileHandler 5MB/3 backup
├── llama-server.log     düz dosya (büyüyebilir)
├── litellm.log          düz dosya
├── agent_bridge.log     Node.js stdout
├── system.log           Kuroshin.bat olay kayıtları
└── disk_cleanup.log     günlük temizlik raporu
```

`scripts/disk_cleanup.sh` her gece 03:00'da çalışır:
- pip cache purge
- 10MB+ logları sıfırla
- HF cache `.incomplete` temizle
- Telegram'a disk durumu bildir

---

## MCP Sunucuları (Claude Code için)

`C:\Kuroshin\.mcp.json` — Claude Code'un kullandığı araçlar:

| MCP | Araç | Açıklama |
|-----|------|----------|
| `kuroshin-echo` | `echo` | Bağlantı testi |
| `kuroshin-search` | `web_search`, `fetch_page`, `fetch_page_deep`, `fetch_page_stealth` | Web erişimi |
| `kuroshin-bridge` | `list_dir`, `read_file`, `write_file`, `bridge_status` | Sistem araçları |
| `kuroshin-walker` | `walker_task`, `walker_status` | RAG + web araştırma (Agno + ChromaDB) |
| `kuroshin-council` | `council_teknisyen`, `council_gozcu` | Ajan Konseyi (Smolagents) |
| `kuroshin-deerflow` | `deerflow_research`, `walker_deep_research` | Otonom araştırma motoru |

`scripts/mcp_toggle.py`: MCP'leri boot'ta aktif, shutdown'da devre dışı bırakır.

---

## Iron Inquisitor v5.2 — Test Sistemi

`scripts/iron_inquisitor/inquisitor_v5.py` — **49 test, 3 test tipi** (18 Mayıs 2026)

| Çalışma | Sonuç | Not |
|---------|-------|-----|
| Tam suite (35 test, servisler kapalı) | 30/35 %88 | 3 boot FAIL beklenen |
| Security suite | **14/14 %100** | Kılıç-kalkan simülasyonu |

- **OpenClaude bağımlılığı YOK** — MCP sunucularını direkt stdio JSON-RPC ile çağırır
- **Self-healing:** Bridge (3005), Walker (9002), llama-server (8080) otomatik başlatılır
- **49 test, 3 test tipi, 19 kategori**
  - `port_check` — 6 servis port kontrolü (boot süreci)
  - `security_check` — **kılıç-kalkan simülasyonu**: 14 test, 4 alt tip (`command`, `injection`, `path_write`, `path_read`)
  - MCP stdio — echo, search, bridge, walker, council, deerflow, memory
- **Güvenlik doğrulaması:** Her boot'ta 14 saldırı senaryosu otomatik test edilir
- **Seçici Çalıştırma:**
  - `--only <id1> <id2>` — sadece belirtilen test ID'leri
  - `--category <cat>` — kategoriye göre filtre (`memory`, `file_ops`, `council`, `web_fetch` vb.)
  - `--skip-passed` — son rapordaki PASS testleri atla, sadece başarısızları yeniden çalıştır
  - `--no-telegram` — yerel test modunda Telegram sessiz
- **chroma-mcp argüman şeması:** `collection_name` (doğru) — `collection` değil
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

**Belirli kategori veya ID:**
```bash
python3 inquisitor_v5.py --category memory --no-telegram --skip-bridge
python3 inquisitor_v5.py --only echo-01 bridge-02 --no-telegram
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
