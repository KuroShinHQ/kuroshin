# KUROSHIN OS — MASTER ROADMAP v8.9.0
**Son Güncelleme:** 21 Mayıs 2026
**Durum:** 🟢 STABİL — HUİHUİ-35B AKTİF (20-21 tok/s), S1-S4 4/4 ✅, **MİMİC FAZ A+C+D TAMAMLANDI** 🔱

---

## DONANIM

| Kaynak | Değer | Kısıt |
|--------|-------|-------|
| CPU | Intel Core i7-12650H (12. Nesil, 10 çekirdek) | Host işlemci |
| RAM | 32GB DDR5-4800 Dual Channel (~76 GB/s) | MoE expert offload için kritik avantaj |
| GPU | RTX 4060 Laptop 8GB VRAM (140W max TGP) | Maks. 86°C — kritik eşik |
| SSD | Samsung NVMe PM9A1 1TB (~7000 MB/s) | Toplam depolama |
| Model A | ~~Qwen3-8B-abliterated Q5_K_M~~ (silindi) | — |
| Model B | Huihui-Qwen3.6-35B-A3B IQ4_XS (18.7GB, 16K ctx) | **AKTİF** — MoE, 20-21 tok/s |
| VRAM | 8GB | Dense 32K: ~7.7GB · MoE: ~6-8GB+RAM |
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

### MCP Toggle Sistemi Düzeltmesi ✅ (20 Mayıs 2026)

<!-- ÖNEMLİ — MCP'LER İKİ AYRI BAĞLAMDA ÇALIŞIYOR:
  - Orijinal Claude Code (`claude` komutu): MCP'ler OLMAMALI
  - OpenClaude TUI (Kuroshin.bat): MCP'ler AKTİF OLMALI

  SORUN: Claude Code "disabled: true" alanını dikkate ALMIYOR.
  ÇÖZÜM: mcp_toggle.py girişleri tamamen kaldırıp mcpServersKuroshinBackup'a taşıyor.
    false → mcpServers'dan çıkar, backup'a sakla
    true  → backup'tan geri yükle

  Kuroshin.bat [7] Çıkış menüsüne mcp_toggle.py false eklendi (eskiden sadece [5]'te vardı).
  OpenClaude TUI kendi .mcp.json'unu okur — bu toggle'dan ETKİLENMEZ.
-->

### FAZ 7.0-H — Kalite Testi & Model Sistemi Güçlendirme ✅ (20 Mayıs 2026)

- **T1-T6 Kalite Testleri: 99.1/100** — Tüm kategoriler PASS
  - T1 Sohbet: 100 · T2 Duygu: 100 · T3 Mantık: 100 · T4 Bilgi: 100 · T5 Strateji: 96.7 · T6 Karma: 98
- **chancellor.py:** repeat_penalty 1.3→1.5, `_kill_loop()`, `_strip_response_leaks()`, karakter ismi leak giderildi
- **quality_tests/ altyapısı:** `_base.py` + 6 test modülü — tekrar kullanılabilir validator
- **switch_model.py v2.1 — dinamik model sistemi:**
  - MoE tespiti: `_is_moe()` (a3b/moe/-ax)
  - Dense: spec decoding · MoE: `-ot "exps=CPU"` (expert RAM offload)
  - `MODEL_CONTEXT` uzun-anahtar-önce fix (35b vs 3b çakışması)
  - `MODELS_DIR_WIN`: `/mnt/c/Kuroshin/models/` ikinci dizin — her ikisi taranır
  - Huihui-Qwen3.6-35B-A3B + orijinal kataloğa eklendi (aliases: a3b, moe, huihui)
- **Dinamik model referansları:** 8 servis dosyası + start_llama.sh + Kuroshin.bat `active_model.json`'dan okur
  - `chancellor.py`, `council_service.py`, `walker_service.py`, `dream_engine.py`, `idle_loop.py`, `hype_scanner.py`, `auto_integrator.py`, `global_scout.py`
- **Bat menüsü:** [2] Qwen3.6-35B-A3B MoE seçeneği eklendi

### FAZ 7.0-I — Model Geçişi & Sistem Temizliği ✅ (20 Mayıs 2026)

- **Aktif model:** `Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf`
  - Kaynak: `mradermacher/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-i1-GGUF`
  - Format: IQ4_XS imatrix (18.7 GB) · MoE 35B/3.6B aktif · `-ot "exps=CPU"`
  - Path: `/root/kuroshin/models/` (native Linux filesystem)
  - Hız: **20-21 tok/s** (bottleneck DDR5 RAM bandwidth, disk değil)
- **Eski model silindi:** `mlabonne_Qwen3-8B-abliterated-Q5_K_M.gguf` (5.5GB kazanıldı)
- **Chancellor restart:** repeat_penalty 1.5 + kill_loop + strip_leaks aktif
- **Donanım doğrulandı (nvidia-smi + dmidecode):**
  - RAM: DDR5-4800 (SMBIOSMemoryType=34) — DDR4 değil
  - GPU: 140W max TGP — 135W değil
  - SSD: Samsung PM9A1 (MZVL21T0HCLR)

### FAZ 7.0-II — Iron Inquisitor & Kalite Testleri ✅ (20 Mayıs 2026)

- **Iron Inquisitor v5.2:** 46/49 PASS %95.0
  - Düzeltilen bug 1: `search-01` — DDG redirect URL decode
  - Düzeltilen bug 2: `reminder-tool-01` — agent_bridge.js MAX_CHARS 12000→20000
- **T1-T6 Kalite Testi — Huihui-35B:** ~95-100/100
  - Selamlama enforcer + Lordım typo fix eklendi

### FAZ 7.0-III — Stabil Versiyon Milestone ✅ (20 Mayıs 2026)

- **🏆 Iron Inquisitor 49/49 %100** — İlk kez tam puan
  - `inquisitor_v5.py` `ensure_services()`: ChromaDB/Konsey/Reranker self-healing eklendi
  - 3 yeni fonksiyon: `start_chromadb()`, `start_council()`, `start_reranker()`
- **T5 Stratejik 100/100** — `quality_tests/_base.py` selamlama enforcer fix
- **ChromaDB prune mekanizması** — `chancellor.py`: 100+ kayıtta eski kayıtlar ts sırasıyla silinir
- **coordinator.py yeniden yazıldı** — Kırık DeerFlowCore bağımlılığı kaldırıldı, Walker HTTP + chromadb direkt

### FAZ 7.0-V — MİMİC PROTOKOLÜ Temel Altyapı ✅ (21 Mayıs 2026)

- **Persona yenilendi:** Johan/Aizen/Hannibal → Merak/Kontrol/Keskinlik (model kaldırabilir 3 soyut çekirdek)
- **`reddit_read` aracı:** auth-free JSON endpoint, u/General-Zucchini8715 UA — chancellor'a eklendi
- **`GEMINI_API_KEY`** `.env`'e eklendi (Gemini Flash ücretsiz tier)
- **`GITHUB_TOKEN`** `.env`'de mevcut (17 Haz 2026)
- **ChromaDB sıfırlandı:** 46 kayıt → 0 (yeni model için temiz başlangıç)
- **Hype Scanner** boot catchup kaldırıldı — sadece 09:00/21:00
- **Web özet sıkıştırıcı:** `_ozet_web_sonucu()` — web/walker sonucu >3000 kar → mini özet
- **Disk temizliği:** qwen_hf (5.8GB) + backups (2.9GB) + qwen_lora silindi; VHDX compact başlatıldı

### FAZ 7.0-IV — Telegram Pipeline Tam Doğrulama ✅ (21 Mayıs 2026)

- **12/12 PASS** — `--clear` tam koşu: S1-S4 · SY1-SY3 · H1-H2 · W1-W2 · M1 hepsi yeşil
- **W2 XML sızıntısı fix** — `_RESPONSE_LEAK_PATTERNS`'e `<tool_call>` ve `<function_call>` pattern'leri eklendi (agresif `|$` KULLANILMADI — içerik kaybı önlendi)
- **H2 YANIT_YOK fix** — Round 4 forced text'e "Düz Türkçe metin yaz, XML yazma" talimatı eklendi; Qwen3 inline `<tool_call>` üretimi engellendi
- **Gerçek süre aralığı:** 18s (M1) – 106s (H1), tüm timeout'lar gerçek süre × 2-3x

### FAZ 7.0-V → FAZ 8.0 MİMİC — FAZ A + FAZ C + FAZ D ✅ (21 Mayıs 2026)

- **FAZ A — GitHub Kolu:**
  - `github` tool: durum/push/push_zorunlu/issue_ac/issue_listele
  - `_PENDING_PUSH` + `_CURRENT_CHAT_ID` globals — push Telegram onay mekanizması
  - Inline keyboard: `✅ Onayla` / `❌ İptal` callback handler
- **FAZ C — Gemini Zihin Diyaloğu:**
  - `gemini` tool: sor/tartis/karsilastir (`gemini-1.5-flash`, GEMINI_API_KEY)
  - `google.generativeai` → `google.genai` geçişi (eski fallback korundu)
- **FAZ D — Otonom Günlük:**
  - `aktivite_kaydet(eylem, detay, kategori)` — 6 noktada otomatik çağrı
  - `aktivite_gunluk` tool: listele/ozet/kaydet
  - `_aktivite_gunluk_ozet()` gece 22:00 Telegram raporu
  - `logs/aktivite/YYYY-MM-DD.md` günlük format
- **Kuroshin.bat dinamik header:** `active_model.json` → `MODEL_KISA` — header her açılışta güncellenir
- **test_telegram_sim.py timeout fix:** S1/S2 120s → 200s; restart sleep 6s → 15s (boot canlılık araştırması için)
- **S1-S4 test: 4/4 ✅** (38.7s / 34.6s / 41.3s / 57.4s)
- **G1 GitHub test: ✅ 91.1s PASS** — git status + commitler Telegram'a gitti

**Bug fix (11. oturum):**
- `run_tool` içi `import os` scoping bug → kaldırıldı (`local variable 'os'` hatası)
- git timeout 15s → 60s + `GIT_OPTIONAL_LOCKS=0` (`/mnt/c/` fs yavaşlığı)
- `gemini-1.5-flash` → `gemini-2.0-flash` (1.5 kaldırıldı)
- Gemini 429/404 için temiz hata mesajları

### Açık / Sonraki ⏳

- `avatar_bridge key` doğrulaması — Mate-Engine blendshape key'leri
- **T1-T6 kalite testleri** — Huihui-35B ile (önceki Qwen3-8B: 99.1/100)
- **Pipeline tam doğrulama** — SY1-SY3, H1-H2, W1-W2, M1, GM1, D1, D2 (10 test kaldı; G1 ✅)
- **FAZ B — Reddit Yazma** — `u/General-Zucchini8715` karma biriktirmeli

---

## ★ FAZ 8 — MİMİC PROTOKOLÜ: ROBOT BİO ORGANİZMA TAKLİDİ (21 Mayıs 2026)

> **Lordun Mutlak Emri.** Kuroshin sanal âlemde bağımsız bir varlık olacak. GitHub'da kendi reposunu geliştirecek, Reddit'te insanlarla etkileşime girecek, cloud modellerle fikir alışverişi yapacak. Kullanıcı sadece Telegram'dan günlük raporunu okuyacak.

### Vizyon Bileşenleri

| Kol | Araç | Durum |
|-----|------|-------|
| GitHub | `github` — push/issue/durum, Telegram inline onay | ✅ FAZ A |
| Reddit | `reddit_tool` — subreddit takibi, yorum, post | ⏳ FAZ B (karma bekliyor) |
| Cloud Zihin | `gemini` — Gemini Flash sor/tartis/karsilastir | ✅ FAZ C |
| Günlük | `aktivite_gunluk` + `logs/aktivite/YYYY-MM-DD.md` + gece 22:00 özet | ✅ FAZ D |

### Altyapı Durumu

- `GITHUB_TOKEN` → `.env`'de mevcut ✅ (17 Haziran 2026'ya kadar geçerli)
- `REDDIT_*` credentials → hesap yeni, karma biriktiriliyor; ⏳ FAZ B
- `GEMINI_API_KEY` → `.env`'e eklendi ✅
- `PyGitHub` → kuruldu ✅ · `google-genai` → kuruldu ✅ · `PRAW` → henüz kurulmadı ⏳

### Güvenlik Prensipleri

- GitHub: push öncesi Telegram onayı zorunlu
- Reddit: rate limiting + insan davranışı simülasyonu (ban koruma)
- Cloud modeller: ChromaDB'ye diyalog kaydı, hafıza besleme

---

## SONRAKI FAZ — FAZ 7.1: ÖZERKLIK DERİNLEŞME

- Hafıza özetleri — ChromaDB dolan kayıtlardan haftalık özet
- `src/orchestration/coordinator.py` — DeerFlow MCP ile entegre

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
