# KUROSHIN OS — MASTER ROADMAP v8.6
**Son Güncelleme:** 18 Mayıs 2026
**Durum:** 🟣 RUH FAZI AKTİF — FAZ 7.0-E TAMAMLANDI, SİSTEM TEMİZLENDİ, FAZ 7.1 SONRAKI

---

## DONANIM

| Kaynak | Değer | Kısıt |
|--------|-------|-------|
| CPU | Intel Core i7 9. Nesil | Host işlemci |
| RAM | 32GB DDR4 | Toplam sistem belleği |
| GPU | RTX 4060 Laptop 8GB VRAM (135W) | Maks. 86°C — kritik eşik |
| SSD | 1TB NVMe | Toplam depolama |
| Model | Qwen3-8B-abliterated Q5_K_M (~5.5GB) | Tek ana beyin, 32K runtime context |
| VRAM | 8GB | 7.5GB eşiğinde servis suspend devreye girer |
| Disk | ~12GB kullanımda | Temizlik yapıldı (18 Mayıs 2026), RotatingFileHandler + disk_cleanup.sh |
| WSL | Ubuntu 22.04 | Tüm Python servisleri WSL içinde |

---

## AKTİF SERVİSLER

| Port | Servis | Dosya |
|------|--------|-------|
| 8080 | llama-server (Qwen3-8B) | `engines/llama.cpp/build/bin/llama-server` |
| 6000 | LiteLLM Proxy | `venv/bin/uvicorn litellm...` |
| 6001 | LitServe | `src/serving/kuroshin_litserve.py` |
| 8100 | ChromaDB | `scripts/start_chromadb.sh` |
| 9002 | Walker Agent | `agents/kuroshin_walker_service.py` |
| 9003 | BGE Reranker | `scripts/kuroshin_reranker_service.py` |
| 9004 | Ajan Konseyi | `agents/kuroshin_council_service.py` |
| 3005 | Agent Bridge (Node) | `scripts/agent_bridge.js` |
| 3006 | Crawlee Bridge (Node) | `tools/crawlee_bridge.js` |
| 8091 | Nuclear Search MCP | `mcp_servers/search_server/kuroshin_engine.py` |
| 8888 | Dashboard | `src/dashboard/kuroshin_dashboard.py` |

---

## TAMAMLANAN FAZLAR

### FAZ 1-5 — Temel Altyapı ✅
ChromaDB, Walker v3.0 (Agno), Agent Bridge, DeerFlow MCP v2.0, LitServe, LLM Router, Gauntlet, Dashboard, Browser MCP, RAG hafıza (ChromaDB persistent).

### FAZ 6.1 — N-Gram Speculative Decoding ✅
`--spec-type ngram-cache --draft-max 16` — sıfır VRAM, %20-30 hız kazanımı.

### FAZ 6.2 — BGE Reranker ✅
Port 9003, `BAAI/bge-reranker-v2-m3`. ChromaDB'den 10 sonuç → 3'e süzer.

### FAZ 6.3 — Ajan Konseyi (Smolagents) ✅
Port 9004. Teknisyen (read/write/shell) + Gözcü (DuckDuckGo). MCP: `kuroshin-council`.

### FAZ 6.4A — Hype Scanner ✅
Sabah 09:00 + Akşam 21:00. GitHub Trending + HF Papers + HF GGUF → Qwen3 analizi → Telegram.

### FAZ 6.4B — Küresel Keşif (Global Scout) ✅
Akşam 20:00. Habr · Gitee · arXiv · HF Datasets · HackerNews → IP skoru → Telegram raporu.

### FAZ 6.5 — Telegram Şansölye v2.1 ✅
8 araç: walker_research · web_search · system_command · memory_query · write_file · read_file · open_url · youtube_play.
ThreadPoolExecutor(4), O_EXCL lock, GPU sıcaklık izleyici, exponential backoff.

### FAZ 6.6 — Otonom Entegrasyon ✅
`auto_integrator.py`: Rapor parse → hf download → speed_test → ChromaDB → Telegram onay kuyruğu.

### EMİR #006 — Sistem Zırhlama ✅ (11 Mayıs 2026)
.env secrets, log rotation, ThreadPoolExecutor, boot healthcheck polling, veri kotası, hata yönetimi, disk cleanup cron, kuroshin_utils ortak kütüphane, birim testler (7/7), ARCHITECTURE.md.

### FAZ 6.7 — Web Katmanı Güçlendirme ✅ (14 Mayıs 2026)
**Walker web erişim zinciri (3 katman, tam fallback):**
1. `web_reader_tool`: Crawl4AI → Camoufox hayalet Firefox
2. `crawlee_deep_crawl`: Crawlee Bridge (port 3006, simple/playwright/stealth) → Crawl4AI → Camoufox

**Crawlee Bridge** (`tools/crawlee_bridge.js`, port 3006):
- 3 mod: simple (native http) | playwright (JS-render) | stealth (navigator.webdriver gizleme)
- Crawlee v3, `require('./node_modules/crawlee/index.js')`, WSL `--no-sandbox` zorunlu

**Camoufox** v0.4.11 — hayalet Firefox, UBO addon, headless. Walker venv'e kuruldu.

**Hivemind Toggle** (`scripts/hivemind_toggle.py`):
- ŞALTER: `HIVEMIND_ENABLED=false` — Kuroshin doktrinini korur, Deeplake'e veri gitmiyor
- Açmak için: `/hivemind_ac` (Telegram) veya `python hivemind_toggle.py on`

**Iron Inquisitor v4.0 — 13/13 PASS %100** (14 Mayıs 2026):
- crawlee-01/02/03 ✅ + crawlee-sync-01 ✅

**Iron Inquisitor v5.1 — 23/23 PASS %100** (17 Mayıs 2026):
- OpenClaude bağımlılığı YOK — direkt stdio MCP protokolü
- Self-healing: Bridge/Walker/llama-server otomatik başlatılıyor
- Yeni 10 test: ChromaDB in-process, model_switch, pdf_reader, proaktif, reminder, memory araçları

---

## FAZ 7.0 — RUH (AKTİF, 16 Mayıs 2026)

### Tamamlananlar ✅

#### FAZ 7.0-A — Ruh Temeli
- `soul/persona.json` — 4 arketip (Johan Liebert + Aizen + Fang Yuan + Hannibal), yasak/tercih ifadeler
- `soul/mood_state.json` — 10 duygu + decay oranları + ilgi_skoru ödül mekanizması
- `soul/MIMARI.md` — 5 katman referans belgesi
- Chancellor THINK+TALK çift tur — İngilizce düşünce → Türkçe yanıt, delta ayrı çağrı
- ChromaDB direkt hafıza — `_get_chroma_context()` son 3 kaydı context'e enjekte eder
- Mood → system prompt dinamik injection (`{mood_line}` + dominant duygu)
- Dashboard soul paneli — duygu dikey barlar + ilgi_skoru + ic_ses.log viewer

#### FAZ 7.0-B — Proaktif Sistemler (16 Mayıs 2026)
- `soul/idle_loop.py` v1.3 — 30dk döngü:
  - Hype/Scout raporları → Telegram özet (HTML escape ile)
  - Merak > 0.6 → Qwen3'ten araştırma önerisi (4s saat cooldown)
  - **Sessizlik decay:** 2s saat → sogukkan artar / 6s saat → derin_dusunce+huzun / 24s saat → yalnızlık bildirimi
  - Sistem sağlık kontrolü 15dk'da bir (startup grace 2dk)
- `soul/dream_engine.py` v1.0 — gece 00:00-06:00:
  - ChromaDB'den 3 anı çeker → Qwen3 rüya sentezi → `logs/dreams/rüya_TARIH.txt`
  - `memory/last_dream.json` sabah referansı için
  - `logs/ic_ses.log`'a da yazar (dashboard görür)
  - Test: "Derin bir buz sessizliği çökmüşken..." ✅

#### FAZ 7.0-C — Emote & İnternet Farkındalığı (16 Mayıs 2026)
- **Emote sistemi:** 10 duygu × 5 emote havuzu → dominant duyguya göre rastgele seçim, yanıtın başına eklenir
- **`internet_status` tool:** Cloudflare/Google/Quad9 DNS + Telegram API kontrolü, 2dk cache
- **İnternet farkındalığı:** `{internet_line}` system prompt'a dinamik enjekte — internet yoksa Qwen3 web_search kullanmaz, yerel kaynaklara yönlenir
- **İlgi skoru her mesajda güncelleme** — slash komutlar dahil her etkileşimde `ilgi_skoru` artar

#### FAZ 7.0-D — Araç Genişletme (16 Mayıs 2026)
- **ChromaDB in-process fix** — `_save_to_chroma()` / `_get_chroma_context()` artık HTTP yerine direkt `chromadb.PersistentClient` kullanıyor. MCP ile aynı data-dir (`/root/kuroshin/memory/chroma`). Her Telegram konuşması kaydediliyor.
- **`model_switch` tool** — Modeller arası tek tool çağrısıyla geçiş. `scripts/switch_model.py`: list/switch/status/history. Geçiş geçmişi `memory/model_history.json`'da. Bat [8] menüsüne de eklendi.
- **`pdf_reader` tool** — PDF URL veya arama terimi → PyMuPDF/pdfminer metin → Qwen3 özet. Mod: ozet/detay/kaydet. Kitap okuma ve ChromaDB'ye kaydetme destekli.
- **`memory_manage` + `chroma_search`** — In-process ChromaDB. listele/ara/sil/arsivle/istatistik.
- **`self_update` + `reminder`** — Konfigürasyon okuma/güncelleme, timed Telegram hatırlatıcı.
- **Proaktif Sohbet Algoritması** (`idle_loop.py v1.4`):
  - `_kullanici_online_mu()` — PC_SCHEDULE'a göre saat kontrolü
  - `_en_guncel_rapor_konusu()` — Son hype/scout raporundan konu çıkar
  - `_proaktif_mesaj_uret()` — Qwen3 kişiselleştirilmiş mesaj
  - Her 3 saatte, online pencerede, Telegram'a sohbet başlatır
  - `memory/ilgi_profili.json` — Kullanıcı tepkilerini öğrenir
- **Bat [8] Model Değiştir** — GUI ile llama-server restart + model geçişi
- **Slash komutlar**: `/bat`, `/bat_stop`, `/model_list`, `/model_status`, `/model_switch`

### FAZ 7.0-D — TAMAMLANDI ✅ (17 Mayıs 2026)

- **Iron Inquisitor v5.1:** 23/23 PASS %100 — self-healing, OpenClaude bağımlılığı yok
- Tüm yeni araçlar test edildi: ChromaDB in-process, model_switch, pdf_reader, proaktif sohbet, reminder
- Çalıştırma: `wsl -d Ubuntu-22.04 --exec /bin/bash -c "source /root/kuroshin/venv/bin/activate && python3 -u /mnt/c/Kuroshin/scripts/iron_inquisitor/inquisitor_v5.py"`

### FAZ 7.0-E — Kalite & Araç İyileştirme ✅ (17 Mayıs 2026)

- **`memory-add-query-01` fix** — chroma-mcp `collection_name` argümanı düzeltildi (`collection` yanlıştı). Benzersiz ID: `inq_<timestamp>`. `tool_called` mantığı "Error executing tool" içeren yanıtları FAIL sayıyor.
- **Skor eşiği Telegram alarmı** — Başarısız test oranı >%30 → 🚨 özel bildirim.
- **eval_feedback_loop.py → Bat [9]** — Menü [9] eklendi: test-only / auto-apply / tek döngü.
- **DeerFlow MCP v2.0** (`mcp_servers/deerflow_server/kuroshin_deerflow_mcp.py`):
  - Subprocess bağımlılığı kaldırıldı — tüm araştırma mantığı inline
  - Crawl4AI → Crawlee Bridge (port 3006) otomatik fallback
  - `sources` parametresi: 1-3 kaynak seçilebiliyor
  - Her araştırma ChromaDB `kuroshin_memory`'ye otomatik upsert
- **Iron Inquisitor v5.2 — Seçici Çalıştırma:**
  - `--only <id1> <id2>` — belirli test ID'leri
  - `--category <cat>` — kategoriye göre filtre (memory, file_ops, council, vb.)
  - `--skip-passed` — son rapordaki PASS testleri atla, sadece başarısızları tekrar çalıştır
  - `--no-telegram` — yerel test için Telegram sessiz
  - council-01 timeout 120s → 240s, `council_gozcu` argümanı `query` → `task` düzeltildi

### FAZ 7.0-G — Güvenlik Duvarı & Kılıç-Kalkan Simülasyonu ✅ (18 Mayıs 2026)

- **`scripts/kuroshin_security.py` v1.0** — Merkezi güvenlik modülü:
  - `check_command()`: 30+ kural — reverse shell, curl|bash, os.system kaçış, /etc/passwd, rm -rf
  - `scan_for_injection()`: 20+ regex — DAN jailbreak, tool injection, sistem prompt etiketleri
  - `sanitize_web_content()`: Web içeriği LLM'e gitmeden önce taranır
  - `check_path_write/read()`: Path traversal koruması
- **Entegrasyon:** `chancellor.py`, `walker_service.py`, `deerflow_mcp.py`
- **Iron Inquisitor v5.2 — 49 test, 3 tip:**
  - `security_check` tipi eklendi — kılıç-kalkan simülasyonu
  - **14/14 security PASS %100** (saldırı + false positive testleri)
  - Test tipleri: `command`, `injection`, `path_write`, `path_read`

### FAZ 7.0-F — Sistem Temizliği & Konsolidasyon ✅ (18 Mayıs 2026)

- **~1.1GB silindi:** `openclaude-main_BACKUP`, `openclaude-main_BACKUP_PROTOKOL_3`, `Kuroshin_CORE_v4.2.9_MASTER`
- **archives/ oluşturuldu:** `old_bats`, `v4.2.9_locked`, `whitelabel`, `outputs`, `patches`, `old_agents`, `old_scripts`, `old_chroma_db`
- **src/ entegrasyona hazır:** ChromaDB path düzeltildi (`/root/kuroshin/memory/chroma`), Qwen3 referansları güncellendi, router docstring temizlendi
- **ARCHITECTURE.md v8.6:** Qwen3, 16 araç, src/ modül katmanı, DeerFlow MCP, disk bilgisi
- **ROADMAP v8.6:** Tüm Qwen3 referansları, temizlik kaydı, Qwen3 thinking mode notu
- Test script çöpleri, path bug dosyaları, GEMINI.md, .bak dosyaları silindi

### Açık / Sonraki ⏳

- ChromaDB kayıt birikimi — Telegram konuşmaları kaydediliyor, dolacak
- `avatar_bridge key` doğrulaması — Mate-Engine blendshape key'leri
- `src/orchestration/coordinator.py` — DeerFlow MCP ile entegre edilebilir

---

## SONRAKI FAZ — FAZ 7.1: ÖZERKLIK DERİNLEŞME

- `soul/dream_engine.py` sabah referansı chancellor entegrasyonu
- Ödül/ilgi algoritması tam implementasyonu (sessizlik cezası + etkileşim bonusu persiste edilsin)
- Kuroshin'in hafıza özetleri — ChromaDB dolan kayıtlardan haftalık özet çıkarsın

---

## HAYIR LİSTESİ (Doktrin)

- **Full Fine-tune / LoRA kalıcı deploy** — RAG > Fine-tune. ChromaDB dış hafıza tercih edilir.
- **vLLM / SGLang** — 8GB VRAM ve WSL2'de dengesiz.
- **Hivemind cloud aktif** — Kuroshin olgunlaşana kadar KAPALI. Şalter: `HIVEMIND_ENABLED=false`.
- **Bulut bağımlılığı** — Tüm çıkarım yerel, 127.0.0.1.

---

## KRİTİK TEKNİK NOTLAR

- **Path:** Her zaman `/mnt/c/Kuroshin/` — `/root/kuroshin/` değil (`kuroshin_user` user)
- **WSL DNS:** `127.0.0.1` kullan — `localhost` IPv6'ya resolve eder
- **Qwen3 thinking mode:** `max_tokens` en az 1500-2000 — aksi halde `reasoning_content` + `content` boş döner. `/no_think` ile düşünce bastırılabilir
- **Agent Bridge safePath:** Yalnızca `C:\Kuroshin\` altına yazar — masaüstü için chancellor Python `Path.write_text()` bypass
- **Crawlee:** `require('./node_modules/crawlee/index.js')` — `dist/` değil. `playwright` paketi zorunlu (playwright-chromium değil)
- **Camoufox:** Walker venv'de (`/root/kuroshin/venv`), headless=True, UBO addon kurulu
- **Bat CRLF:** `sed -i` LF'e dönüştürür — Write tool veya PowerShell kullan
- **O_EXCL lock:** `fcntl.flock()` WSL cross-session'da çalışmıyor — Chancellor ve hype_scanner O_EXCL flag'li open() kullanır
