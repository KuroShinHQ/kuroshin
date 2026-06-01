# Kuroshin OS — KILAVUZ (yeni geliştirici / Claude için)
**Sürüm:** v11.15.0 — 1 Haziran 2026

> Bu dosya **giriş kapısı**. Sisteme yabancı biri buradan başlasın. Detaylar diğer MD'lerde.

---

## 📚 Sadece 3 Core MD oku, başla

| Sıra | Dosya | Ne için |
|------|-------|---------|
| 1 | [`KUROSHIN_MASTER_ROADMAP.md`](KUROSHIN_MASTER_ROADMAP.md) | Sürüm geçmişi (v8.6 → v11.4.0), her dalga ne yapıldı, kanıt raporlar |
| 2 | [`ARCHITECTURE.md`](ARCHITECTURE.md) | Donanım, port haritası, servisler, KILIÇ-KALKAN, Iron Inquisitor yapısı |
| 3 | [`GOREVLER.md`](GOREVLER.md) | Aktif TODO, dalga planları, Lord onay komut yapıları |

> **Eski `YAPILACAK_GOREVLER.md` root'tan kalktı** → `docs/`'ta tarihsel arşiv.

---

## 🗂️ Klasör haritası (kısa)

```
C:\Kuroshin\
├── KUROSHIN_MASTER_ROADMAP.md  ← v11.4.0 sürüm geçmişi
├── ARCHITECTURE.md             ← sistem mimarisi
├── GOREVLER.md                 ← aktif TODO + dalga planları
├── KILAVUZ.md                  ← bu dosya
├── Kuroshin.bat                ← Windows başlatıcı (v11.1.0 menü)
│
├── agents/
│   └── kuroshin_chancellor.py  ← Telegram bot, 24 araç, KILIÇ-KALKAN entegre
│
├── scripts/
│   ├── kuroshin_security.py    ← KILIÇ-KALKAN v4 — 24 fonksiyon
│   ├── kuroshin_autonomous.py  ← Otonom ajan (OODA + Reflexion + Plan-and-Execute)
│   ├── kuroshin_goals.py       ← goals/tasks CRUD
│   ├── kuroshin_md_agent.py    ← MD öz-güncelleme
│   ├── kuroshin_telegram_ajan.py
│   ├── switch_model.py         ← Model değiştirme + A/B test
│   ├── start_llama.sh          ← llama-server başlatıcı (active_model.json'dan dinamik)
│   ├── gen_params_ab.py        ← Generation params A/B harness
│   ├── tool_usage_report.py    ← 7/30 gün tool histogramı
│   └── iron_inquisitor/
│       ├── inquisitor_v5.py    ← Ana tester (code_inspect dahil 18+ check tipi)
│       ├── master_manifest.json  ← 3 tier (core 153 + extended 50 + historical 30)
│       ├── test_suite_verify_v11.json  ← Dalga 1-4 otomatik kanıt (48 test)
│       ├── test_suite_security_v2/v3/v4/v5.json  ← KILIÇ-KALKAN testleri
│       ├── test_suite_full_v2.json  ← MCP + tool kullanım
│       ├── test_suite_think.json    ← Think chain TK-01~09
│       └── test_suite_ajan.json     ← Otonom ajan
│
├── soul/
│   └── idle_loop.py            ← OODA probe, sessizlik decay, yokluk dispatcher (D-A6)
│
├── docs/                       ← Tarihsel + plan arşivi
│   ├── YAPILACAK_GOREVLER.md   ← v8.6 → v10.7 tarihçe
│   ├── OTONOM_AJAN_PROTOKOLU.md  ← FAZ 1-13 tasarım
│   ├── THINKING_QUALITY.md     ← TK-01~09 tarihçe
│   ├── OPTIMIZATION.md         ← rename planı (KAPANDI)
│   └── PLAN_DALGA2_EXTRA.md    ← Llama Guard 3 + Qwen3-30B kurulum prosedürü
│
├── memory/                     ← Runtime state (çoğu .gitignore'da)
│   ├── active_model.json       ← Aktif LLM model
│   ├── goals.json / tasks.json / task_context.json
│   ├── reflexion_buffer.json   ← E-05 Reflexion verbal buffer
│   ├── son_selam_ts.txt        ← D-A3 selamlama timestamp (kalıcı)
│   ├── prompt_integrity.json   ← BLUE-NEURAL-01 SHA256 hash
│   └── reflections/, md_backups/, genparams_ab_reports/, ab_test_reports/
│
├── logs/
│   ├── chancellor.log          ← RotatingFileHandler 5MB/3
│   ├── autonomous.log
│   ├── think_chain/YYYY-MM-DD.jsonl  ← OTel GenAI attribute'larıyla
│   ├── audits/YYYY-MM-DD.jsonl       ← SHA256 hash zinciri
│   └── aktivite/YYYY-MM-DD.md        ← Otonom günlük
│
└── openclaude-main/
    └── CLAUDE.md               ← OpenClaude TUI Kuroshin persona (D-C1)
```

---

## 🚀 Test çalıştırma (sistem kapalıyken)

```bash
# Verify suite — Dalga 1-4 helper varlık doğrulaması (~5s, offline)
wsl -d Ubuntu-22.04 -e /bin/bash -c "cd /mnt/c/Kuroshin && python3 scripts/iron_inquisitor/inquisitor_v5.py --suite test_suite_verify_v11.json --skip-llama --skip-bridge --no-telegram"

# Security suite (offline, ~10s)
wsl -d Ubuntu-22.04 -e /bin/bash -c "cd /mnt/c/Kuroshin && python3 scripts/iron_inquisitor/inquisitor_v5.py --suite test_suite_security_v2.json,test_suite_security_v3.json,test_suite_security_v4.json,test_suite_security_v5.json --skip-llama --skip-bridge --no-telegram"

# Tier core canlı (sistem ayakta olmalı, ~15-30dk)
wsl -d Ubuntu-22.04 -e /bin/bash -c "cd /mnt/c/Kuroshin && python3 scripts/iron_inquisitor/inquisitor_v5.py --manifest master_manifest.json --tier core --no-telegram"
```

## 🟢 Sistem başlatma

```
Kuroshin.bat → [1] Walker Modu
```
Tüm servisler (llama-server 8080, ChromaDB 8100, Walker 9002, Konsey 9004, Reranker 9003, Bridge 3005, Search 8091, Chancellor 8201) ~90s'de ayakta.

## 🛡️ Aktif Model
**Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated IQ4_XS** — 18.7 GB, **256K ctx (262144)** ⭐ v11.5.0, prompt 163 tok/s + gen 17-22 tok/s
- Path: `/root/kuroshin/models/`
- start_llama.sh `active_model.json`'dan dinamik okur
- **Native max:** `qwen35moe.context_length = 262144` (GGUF kanıtı — `scripts/_inspect_gguf.py`)
- **KV cache (Q4_0):** ~12 KB/token → 256K ≈ 3 GB VRAM (8 GB GPU'da rahat sığar)
- **Needle@76K PASS:** `scripts/_test_long_ctx_retrieval.sh` ile doğrulandı (30 May 2026)
- **Qwen3-30B-2507 denendi, A/B'de Huihui'ye yenildi (Lordum %60 vs %10-33), silindi**

---

## 📜 Lord (kuroshin_user) Kuralları (KRİTİK)

1. **Manuel test YASAK** — Sistem kendi test edemiyorsa o görev planlanmaz. Iron Inquisitor `code_inspect` ile otomatize edilebilirse yapılır.
2. **Kanıtsız iş = geri al/kapat** — Test rapor/metrik yoksa özellik silinir, açıkça raporlanır.
3. **Tam otonom yetki** — Disk/RAM/servis/indirme komutları için sorma. Test edip kanıt sun.
4. **Bekle = pasif** — "Bekle" denilince yeni iş başlatma.
5. **Root'ta 3 MD** — Yeni MD'ler `docs/`'a.

Detay: `memory/feedback_lord_kurallari.md` (Claude memory sistemi)

---

## 🔁 STANDART İŞ AKIŞI — Yeni Özellik = Otomatik Test (31 May 2026 doctrine)

Lord "test et" yazmasa bile, **yeni özellik gelirse** veya **kod değişirse** Claude otomatik şu 5 adımı çalıştırır:

### 1. Pre-flight check
- VRAM/RAM/disk yeterli mi (`scripts/kuroshin_hw_guard.py`)
- Web research: 2026 SOTA, alternatif yaklaşımlar
- Bağımlılık analizi (yeni pip paket → boyut + risk)

### 2. Uygulama
- Bağımsız modül yaz (production chancellor.py'a dokunma — gerekirse minimal tool ekle)
- Lazy import (boot etkisi sıfır)
- Safe fallback (hata = string return, ana akış bozulmaz)

### 3. Çift kanıt
- **Offline:** Iron Inquisitor `code_inspect` (file_exists + file_contains)
  - Yeni `test_suite_dalgaX.json` veya mevcut suite'e ek
  - Hedef: %100 PASS, regression yok
- **Live:** Telegram inject suite (`scripts/_live_test_full_suite.py`)
  - chancellor.log'dan `[TELEGRAM_OUT]` izle
  - Format kontrol: `⚔️ Lordum`, markdown yok, think leak yok
  - Hedef: ≥%80 PASS

### 4. MD update (zincir)
- `KILAVUZ.md` — sürüm + son durum
- `KUROSHIN_MASTER_ROADMAP.md` — yeni versiyon entry
- `GOREVLER.md` — dalga checklist
- `memory/MEMORY.md` + `project_kuroshin.md` — auto-memory (gelecek session için)

### 5. Commit
- HEREDOC ile commit message (kanıt zinciri + skor + dosyalar)
- Push: sadece Lord açıkça istediğinde

### Bug bulununca
- Aynı 5 adımı tekrar et
- Test rapor JSON'a yaz (`scripts/iron_inquisitor/reports/`)
- "Düzeltildi" demek yetmez — yeni Iron Inquisitor test ekle ki regression olmasın

### Tools / Komutlar
- **Restart Chancellor (yeni kod aktif):** `wsl -d Ubuntu-22.04 -e /bin/bash -c "bash /mnt/c/Kuroshin/scripts/restart_chancellor.sh"`
- **Live inject test:** `python3 /mnt/c/Kuroshin/scripts/_live_test_full_suite.py`
- **Tek inject:** `echo '{"chat_id":YOUR_TELEGRAM_CHAT_ID_HERE,"text":"...","test_mode":true}' > /tmp/kuroshin_test_inject.json`
- **Master verify:** `python3 scripts/iron_inquisitor/inquisitor_v5.py --manifest scripts/iron_inquisitor/master_manifest.json --tier core`
- **HW Guard status:** `python3 -c "from kuroshin_hw_guard import short_status_line; print(short_status_line())"`

---

## 🏆 Son durum (v11.15.0 — 1 Haz 2026)

- **DALGA 5.1-5.6 ✅** Context 256K + Hybrid RAG + Episodic + LangGraph + Full Power + HW Guard
- **BÜYÜK TEST + BUG FIX (v11.11) ✅** Live 6/6 + 5 bug fix + MD doctrine
- **KILIÇ-KALKAN v6 ✅** 5 yeni saldırı (ChatInject + Data exfil + RAG indirect + Rug pull + Tool chain), 14/14 live verify
- **WEB SCRAPER RESILIENCE ✅** UA rotation + Sec-Fetch headers + 8 anti-bot signature + cookie persist
- **GPU_WATCHER FIX ✅** subprocess → NVML (log spam bitti)
- **KONSOLİDASYON v11.13 ✅** Tool schema audit (AST denetçi, regresyon muhafızı), `restart_chancellor.sh` sağlamlık (setsid + AKTİF/8201 doğrulama + Telegram alarm), repo hygiene (13 throwaway sil, 5 state .gitignore)
- **ENTEGRASYON BORCU v11.14 ✅** Hybrid RAG normal yola bağlandı (`_get_chroma_context`→`_retrieve_for_context`, no-rerank). **Kanıt güdümlü:** `_measure_retrieval.py` top-3 → hybrid-norerank %100 vs dense %83.3 (+16.7pp); reranker küçük corpus'ta noise → `use_reranker=False`. Safe fallback plain dense. Canlı: `[RETRIEVAL] hybrid-norerank top3`. quality_fix **14/14**
- **EPISODIC CANLI v11.15 ✅** chancellor `_persist_conversation` her gerçek turu episodic'e yazar; `_get_episodic_context` user-scoped + threshold 0.45 (sparse-noise filter); LIVE pipeline: 86421 fact write→read (count 0→2, recall **doğru cevap**)
- **Iron Inquisitor:** 48/48 verify_v11 + **74/74 dalga5+v6+scraper+episodic-entegrasyon** + 73/73 security + 103/104 canlı tier_core (toplam 307 test)
- **TELEGRAM KALİTE FIX (31 May 2026) ✅** Tur-1: FIX-1 `system_info` şeması `konu`'yu zorunlu sanıp E-13 döngüsüyle kırıyordu → `required:[]`; FIX-2 yetim variation selector (U+FE0F) stripi. Tur-2 (A+B): **A** patchright chromium-1208 kuruldu (Crawl4AI stealth — search-02 PASS); **B1** SYSTEM_PROMPT "OLGUSAL SORULAR" disiplini (tarih uydurma→system_info, systemctl yasak, persona gevezeliği yok); **B2** orchestrator synthesis grounding (full_power systemctl→`restart_chancellor.sh`, markdown yok); **B3** dengesiz tırnak temizliği + 'yapay zeyam' typo kimlik-leak deseni. NOT: SYSTEM_PROMPT değişince `memory/prompt_integrity.json` re-lock şart (BLUE-NEURAL-01). Kanıt: `_verify_quality_fixes.py` 8/8 + `test_suite_quality_fix.json` **8/8** + live suite 6/6 (T6 systemctl→restart_chancellor.sh, T3 tarih uydurmuyor, T2 tırnak temiz, T1 VS temiz)
- **KILIÇ-KALKAN:** 24 fonksiyon, ASR 0%, 53/53 saldırı engellendi
- **Tool:** 24 araç, schema-validated + scoring
- **Otonom:** Reflexion buffer + Plan-and-Execute aktif
- **Observability:** OTel GenAI + Prometheus + ChromaDB latency
- **Disk:** WSL %9 kullanım (81 GB / 1007 GB) — 36 GB geri kazanıldı
- **Son commit:** `9c239be` (konsolidasyon) — 13 commit `origin/main` önde, push beklemede
