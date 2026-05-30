# Kuroshin OS — KILAVUZ (yeni geliştirici / Claude için)
**Sürüm:** v11.8.0 — 30 Mayıs 2026

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

## 🏆 Son durum (v11.8.0 — 30 May 2026)

- **DALGA 5.1 ✅** Context 16K → **256K (16x kazanım)** — needle@76K PASS, regression 48/48 korundu
- **DALGA 5.2 ✅** Hybrid RAG (BM25+Dense+RRF+CrossEncoder) — `scripts/kuroshin_rag.py`, ortalama latency 852ms
- **DALGA 5.3 ✅** Episodic Memory (3 katman) — `scripts/kuroshin_episodic.py`, cross-session 5/5
- **DALGA 5.4 ✅** LangGraph Orchestrator — `scripts/kuroshin_orchestrator.py`, baseline %0 → multi-agent %100 (+100 pp), %30 daha hızlı
- **Iron Inquisitor:** 48/48 verify_v11 + **33/33 dalga5** + 73/73 security + 103/104 canlı tier_core (toplam 266 test)
- **KILIÇ-KALKAN:** 24 fonksiyon, ASR 0%, 53/53 saldırı engellendi
- **Tool:** 24 araç, schema-validated + scoring
- **Otonom:** Reflexion buffer + Plan-and-Execute aktif
- **Observability:** OTel GenAI + Prometheus + ChromaDB latency
- **Disk:** WSL %9 kullanım (81 GB / 1007 GB) — 36 GB geri kazanıldı
- **Son commit:** `0fbeb50` (Dalga 5.1 commit beklemede)
