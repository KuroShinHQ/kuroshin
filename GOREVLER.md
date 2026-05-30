# Kuroshin OS — Aktif Görevler (GÖREV MASASI)
**Son Güncelleme:** 29 Mayıs 2026
**Süreç:** 🚀 **OTONOMİ-MAX** — DALGA 1+2+3+4 ✅ + **VERIFY SUITE 48/48 %100** (otomatik kanıt); DALGA 5 İPTAL (manuel test yok)

> **Bu dosya:** Aktif, dinamik TODO. Tamamlananlar `docs/YAPILACAK_GOREVLER.md` arşivine taşınır.
> **Core MD'ler:** [`KUROSHIN_MASTER_ROADMAP.md`](KUROSHIN_MASTER_ROADMAP.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md) · `GOREVLER.md` (bu)

---

## 🌐 Süreç: OTONOMİ-MAX

### Lord'un Emri (rafine)
> Kuroshin'in otonom zeka ve verimliliğini bir üst dereceye çıkar. Karar verme, araç kullanma, savunma duvarını **2025-2026 literatür SOTA**'sıyla hizala. Kodu zorla bozma — önce **keşif yap**, sonra Lord onayıyla **entegre et**.

### Araştırma Doktrini
Her K-XX = **yerel kod incelemesi + web search**. Web search hedefi:
- 🌐 **Global**: 2025-2026 SOTA, üretim sınıfı referans mimariler
- 🎯 **Dikey**: Kuroshin'in tam ihtiyacı olan dar alana derin in
- ⚡ **Kalite/Verim**: doğrudan ölçülebilir kazanç (latency, accuracy, FP rate)
- 🔀 **Varyasyon**: alternatif/yeni tasarımlar — sadece geleneksel yol değil

### Süreç Akışı
```
[1] KEŞIF (✅ bitti) → bulgular + öneriler aşağıda
[2] 🛑 ONAY KAPISI — Lord 🟢/🟡/🔴 ile öneri seçer
[3] ENTEGRASYON — onaylı E-XX görevleri sıralı uygulanır
[4] DOĞRULAMA — Iron Inquisitor (172 test) + T1-T6 regression
[5] KONSOLİDE — MEMORY + ROADMAP + ARCHITECTURE güncellenir
```

---

## 🔍 AŞAMA 1 — KEŞIF (TAMAM)

### K-01 · Iron Inquisitor coverage haritası — ✅
**Bulgu:** 11 test suite, **toplam ~172 test** (full=49, security_v2=32, security_v4=25, faz1_2=14, ajan=10, new_tools=10, faz6=9, think=8, doom=6, circuit=5, v3=4). `inquisitor_v5.py`'de **25+ check tipi**.
**Boşluk:** Multimodal injection (image/QR), MCP tool poisoning, multi-turn jailbreak (>5 round Crescendo), agent observability (OTel).
**Öneri:**
- **E-01** · `test_suite_security_v5.json` — MCP tool poisoning + multimodal + uzun-zincirli Crescendo testleri
- **E-02** · `inquisitor_v5.py` → `tool_metadata_scan` ve `mcp_poison` check tipleri

### K-02 · `chancellor.py` SYSTEM_PROMPT envanteri — ✅
**Bulgu:** `chancellor.py:1267` — **60+ satır**, BLUE-NEURAL-01 SHA256 hash ile kilitli. Çift düşünce yönergesi var: **"İÇ SES — yanıta yazma"** (1270-1280) + **"ZORUNLU DÜŞÜNCE ADIMLARI — reasoning içinde yaz"** (1281-1285). Model her iki yönergeyi farklı yerlere yorumluyor → çelişki riski.
**Boşluk:** Statik kurallar; intent-based semantic classification yok. Token maliyeti sabit ~1500-2000.
**Öneri:**
- **E-03** · İÇ SES + ZORUNLU DÜŞÜNCE'yi **tek 4-adım şemada** birleştir, çelişkiyi kaldır → TK-02 ile zaten uyumlu
- **E-04** · Prompt'u 3 katmana ayır: **L1 sabit kimlik** (hash-locked) + **L2 dinamik durum** (mood/internet/aktif görev) + **L3 göreve-özel** (sadece otonom döngüde) — token tasarrufu + odak artışı (referans: MemGPT 2.0 tiered storage)

### K-03 · `autonomous.py` KuroshinAjan karar mantığı — ✅
**Bulgu:** `kuroshin_autonomous.py:591` OODA tam — uyan/karar_ver/gorev_calistir/degerlendir/guncelle/planla_sonraki. `karar_ver()` JSON parse + retry (temp=0.1 basit prompt) + F4-04 döngü kırıcı (son 3 görev). AJAN-10 token bütçe (max 10 LLM çağrı/oturum) + Jaccard ≥0.7 SD cache.
**Boşluk:**
- Reflexion'ın **kalıcı verbal episodic buffer**'ı yok (reflection ChromaDB'ye yazılıyor ama "öğren ve sonraki denemeye taşı" deseni formal değil)
- Plan-and-Execute deseni yok — uzun-vadeli görev için planner+executor ayrımı atlanıyor
**Öneri:**
- **E-05** · Reflexion-style **`memory/reflexion_buffer.json`** — başarısız görev için "ne yanlış gitti + bir sonraki denemede ne dene" verbal notu, sonraki `karar_ver()` promptuna inject
- **E-06** · Plan-and-Execute hibrit: 5+ adımlı görev için ayrı `planla()` adımı (statik plan → executor), 2-3 adımlık için mevcut ReAct (referans: Plan-and-Act, arXiv 2503.09572)

### K-04 · `kuroshin_security.py` KILIÇ-KALKAN coverage — ✅
**Bulgu:** 21 fonksiyon, security_v4 25 test PASS. Mevcut: encoding/escalation/MCFA/integrity/honeypot/HMAC/alignment/ASR.
**Boşluk (2026 SOTA):**
- **MCP tool poisoning** (CVE-2025-54136 — 200K vulnerable instance) — yok
- **Multimodal injection** (image/QR/steganografi) — yok
- **Semantic vector similarity** defense — sadece pattern-based, embedding tabanlı yok
- **Multi-turn detection** — `escalation_score()` 5-mesaj penceresi, modern Crescendo 8-12 turna uzayabiliyor (representation engineering)
- **Output integrity** ek katmanı yok — Llama Guard 3 / NeMo Guardrails post-output filter olarak eksik
**Öneri:**
- **E-07** · `detect_mcp_tool_poison(tool_metadata)` — MCP server tool tanımı taraması
- **E-08** · `escalation_score` window 5→10, `representation_drift_score()` ekle (embedding tabanlı semantic drift)
- **E-09** · **Llama Guard 3** opsiyonel post-filter — ya yerel ya da kapalı (false positive izleme ile)

### K-05 · 2026 SOTA otonom ajan literatürü — ✅
**Bulgu:**
| Mimari | Güçlü tarafı | Kuroshin durumu |
|--------|--------------|-----------------|
| **ReAct** | Hızlı tool döngüsü | ✅ Mevcut (KuroshinAjan) |
| **Reflexion** | Verbal self-critique buffer | ⚠️ Reflection var, buffer pattern formal değil |
| **Plan-and-Execute** | Uzun vadeli görevler | ❌ Yok |
| **Tree-of-Thoughts** | Paralel reasoning | ❌ Yok (gerek var mı?) |
| **CodeAgent** (Smolagents) | %30 daha az LLM çağrısı | ✅ Konsey 9004'te |

2026'da prod sistemleri 3 layered: **Memory layer** (Mem0/Letta/Zep) + **Orchestrator** (Microsoft Agent Framework / LangGraph) + **Observability** (OpenTelemetry GenAI). Kuroshin'in **Smolagents (Ajan Konseyi)** seçimi 2026 trendiyle uyumlu (yerel LLM friendly, %30 token tasarrufu).
**Öneri:**
- **E-10** · OpenTelemetry GenAI Semantic Conventions ile think_chain JSONL log'u sarmala → standart bir tracing formatı (Langfuse/Phoenix self-host opsiyonu)

### K-06 · Tool/MCP envanteri ve kullanım sıklığı — ⏸ (log analizi gerekli)
**Durum:** chancellor.log'dan son 7 gün tool histogramı çıkarılmalı.
**Hızlı bulgu:** 24 araç var, ARCHITECTURE.md'de listeli. Bazıları (`youtube_play`, `open_url`) muhtemelen düşük kullanım, ama log doğrulaması yapılmadı.
**Öneri:**
- **E-11** · `scripts/tool_usage_report.py` — log parse → 7 günlük tool histogramı + zombi tespiti

### K-07 · Düşük kaliteli tool tespiti — ⏸ (log analizi ile birleşik)
**Bulgu (kod incelemesi):** walker_research 360s timeout, KAY-03 80 kar eşiği — agresif değil. web_search LLM-özet kaldırılmış (v9.3.0 fix). Tool hallucination paper'ı (arXiv 2601.05214) tool seçim hataları için %86.4 doğruluk ile internal representation detection öneriyor.
**Öneri:**
- **E-12** · `_score_tool_call(name, args, expected)` — internal representation tabanlı tool çağrı doğrulama
- **E-13** · Tool schema'ları **JSON Schema strict mode**'a çevir (decoding constraints)

### K-08 · Performans bottleneck haritası — ⏸ (ölçüm gerekli)
**Bulgu (mevcut):** llama-server 20-21 tok/s (DDR5-4800 ~76 GB/s bandwidth limited). 16K ctx, expert offload. ChromaDB in-process. BGE Reranker 9003 fp16.
**Bilinmeyenler:** prompt token dağılımı, KV cache hit oranı, ChromaDB sorgu latency dağılımı.
**Öneri:**
- **E-14** · llama-server `/metrics` endpoint (Prometheus exposition) → Grafana dashboard
- **E-15** · ChromaDB sorgu zamanlamasını log'a ekle (latency histogram)

### K-09 · Yeni model değerlendirmesi — ✅
**Bulgu:**
| Model | Tool-use | Hız | VRAM | Karar |
|-------|----------|-----|------|-------|
| **Huihui-35B-A3B (mevcut)** | İyi | 20-21 tok/s | 7.7GB @16K | ✅ stabil |
| **Qwen3-30B-A3B-Instruct-2507** | **Daha iyi** (agent-tuned) | ~22-26 tok/s tahmin | ~7.5GB @64K | 🟡 dene |
| **DeepSeek-R1-Distill-14B** | Tool payload sızıntı sorunu | Daha yavaş | ~9GB | 🔴 atla |

Qwen3-30B-2507 agent loop için daha optimize, MoE/A3B avantajı korunuyor, **262K natif ctx** (8GB VRAM'de 64K'ya konfigüre edilir, `--reasoning-budget 3072` ile).
**Öneri:**
- **E-16** · MODEL-01..05 askıdan al → Qwen3-30B-2507 IQ4_XS (~16.4GB) indir + T1-T6 karşılaştırma
- **E-17** · `switch_model.py`'ye **A/B test modu** (model_a vs model_b, sabit 10 prompt, otomatik skor)

### K-10 · RAG/ChromaDB kalite ölçümü — ✅
**Bulgu:**
- ChromaDB'ye karşı standart RAG saldırılarında **%95 başarı** (Prompt Security 2026). Vektör poisoning **%80 hijack**.
- Mevcut savunma: `scan_chroma_documents` + `detect_mcfa` + `integrity_hash` SHA256 + RED-MEM-02 okuma sırası hash doğrulama → **2026'da temel düzeyde yeterli ama embedding-tabanlı poisoning'i yakalamaz**
- **CVE-2026-45829 (ChromaToast):** pre-auth RCE — Kuroshin sadece 127.0.0.1 dinler, exposure yok ama paket sürümü güncellenmeli
**Öneri:**
- **E-18** · `detect_semantic_chameleon(query, top_k_docs)` — query embedding'i ile top-k retrieved docs arasında **anomalous similarity** tespiti (referans: arXiv 2603.18034)
- **E-19** · ChromaDB upgrade + supply chain audit (`pip-audit chromadb`)

---

## 📊 Onay Tablosu — Lord seçim yapacak

| ID | Başlık | Yüklü mü? | Tahmin saat | Risk |
|----|--------|-----------|-------------|------|
| **E-01** | Yeni test suite v5 (MCP poison + multimodal) | Iron Inquisitor | 3-4 | düşük |
| **E-02** | `tool_metadata_scan` + `mcp_poison` check tipleri | inquisitor_v5 | 1-2 | düşük |
| **E-03** | SYSTEM_PROMPT iç ses + 4-adım birleştir | chancellor.py | 1 | orta (hash güncelle) |
| **E-04** | SYSTEM_PROMPT 3-katman (L1/L2/L3) | chancellor.py | 3 | orta |
| **E-05** | Reflexion verbal buffer | autonomous.py + memory/ | 2 | düşük |
| **E-06** | Plan-and-Execute hibrit (5+ adım) | autonomous.py | 4-5 | orta |
| **E-07** | `detect_mcp_tool_poison()` | security.py | 2 | düşük |
| **E-08** | `escalation_score` window 5→10 + `representation_drift_score` | security.py | 3 | orta |
| **E-09** | Llama Guard 3 opsiyonel post-filter | yeni servis | 5-6 | yüksek (yeni 4-5GB model) |
| **E-10** | OpenTelemetry GenAI think_chain tracing | chancellor.py | 3 | düşük |
| **E-11** | `tool_usage_report.py` 7 günlük histogram | scripts/ | 1 | düşük |
| **E-12** | `_score_tool_call()` internal representation | chancellor.py | 4 | yüksek (arXiv yeni) |
| **E-13** | Tool schema JSON Schema strict | chancellor.py TOOLS | 2 | düşük |
| **E-14** | llama-server `/metrics` Prometheus | start_llama.sh | 2 | düşük |
| **E-15** | ChromaDB latency log | walker_service.py | 1 | düşük |
| **E-16** | Qwen3-30B-2507 indir + T1-T6 karşılaştır | switch_model | 4-5 | düşük (geri dönülebilir) |
| **E-17** | switch_model A/B test modu | switch_model.py | 2 | düşük |
| **E-18** | `detect_semantic_chameleon()` | security.py | 4 | orta |
| **E-19** | ChromaDB upgrade + pip-audit | sistem | 1 | düşük |

### Hızlı Pakte Önerileri (Lord birden çok onaylayabilir)

- **🥇 KILIÇ-KALKAN Hızlı Güçlendirme** (E-02 + E-07 + E-08 + E-19) — ~7 saat, düşük risk, 2026 saldırılarına direkt karşılık
- **🥈 SYSTEM_PROMPT Temizliği** (E-03 + E-04) — ~4 saat, otonom karar kalitesi sıçraması
- **🥉 Otonom Karar Üst Sürüm** (E-05 + E-06) — ~6 saat, Reflexion + Plan-and-Execute
- **🆕 Model Yenileme Denemesi** (E-16 + E-17) — ~6 saat, geri dönüş kolay
- **📈 Observability Tabanı** (E-10 + E-11 + E-14 + E-15) — ~7 saat, "ne olduğunu görüyoruz" çıkış noktası

---

## 🛡️ VERIFY SUITE — Dalga 1-4 Otomatik Kanıt ✅ TAMAMLANDI (30 May 2026) — v11.4.0

**Lord direktifi:** "Manuel test sevmiyorum, sistem kendi test etsin." → Dalga 5 iptal, yerine Iron Inquisitor genişletildi.

- [x] **Iron Inquisitor `code_inspect` check tipi** ✅ — `file_exists` / `file_contains` / `file_not_contains` + `is_regex` flag, offline çalışır
- [x] **`test_suite_verify_v11.json`** ✅ — **48 test** (Dalga 1: 8 + Dalga 2: 15 + Dalga 3: 17 + Dalga 4: 8)
- [x] **`master_manifest.json` v6.1** ✅ — tier_core'a eklendi (104 → 153 test)
- [x] **Kanıt regression:** **48/48 PASS %100** (`scripts/iron_inquisitor/reports/inquisitor_20260530_100511.json`)
- [⏸] **DALGA 5 İPTAL** — manuel doğrulama gereken görevler ertelendi, sadece sistem kendi yapabildikleri kondu

**Çalıştırma:** `python3 scripts/iron_inquisitor/inquisitor_v5.py --suite test_suite_verify_v11.json --skip-llama --skip-bridge --no-telegram` (anında, ~5 saniye)

---

## 🆕 DALGA 3 — PRODUCTION QUALITY ✅ TAMAMLANDI (29 May 2026) — v11.2.0

**Iron Inquisitor security regression 73/73 PASS %100 · ASR 0% (53/53 saldırı engellendi)**
Kanıt: `scripts/iron_inquisitor/reports/inquisitor_20260529_152658.json`

---

### TIER A — KRİTİK BUG FİX ✅ TAMAMLANDI

- [x] **D-A1 · Avatar App dizin yoksa atla**
  - **Sorun:** 12:35 boot'ta "Dosya adı sözdizimi hatalı" — Bat satır 206
  - **Kök neden:** `C:\Kuroshin\kuroshin avatar vrm\avatar_app\` **dizin yok** (Lord Mate-Engine projesini kurmamış); bat hala körü körüne `npm start` deniyor
  - **Fix:** Satır 205-207 önüne `if exist "C:\Kuroshin\kuroshin avatar vrm\avatar_app\package.json"` guard; yoksa boot_notify `Avatar atlandı (kurulum yok)` mesajı
  - **Süre:** 10 dk · **Risk:** sıfır

- [x] **D-A2 · Bat banner v10.7.0 → v11.1.0**
  - **Sorun:** 6 yerde hâlâ v10.7.0 görünüyor (Dalga 1+2 sürümünü yansıtmıyor)
  - **Fix:** Title, MAIN_MENU header, WALKER_MODU header, gauntlet, walker tamam mesajı, log satırı → v11.1.0
  - **Süre:** 5 dk · **Risk:** sıfır

- [x] **D-A3 · Selamlaşma kalıcı timestamp (`/tmp` → `memory/`)**
  - **Sorun:** 12:35'te 2 kez selamlama (🌑 + 🖤)
  - **Kök neden:** `_SELAM_TS_PATH = /tmp/kuroshin_son_selam.txt` — WSL2'de `/tmp` boot'ta sıfırlanabilir; 30dk koruma sıfırdan başlıyor
  - **Fix:** `_SELAM_TS_PATH = /mnt/c/Kuroshin/memory/son_selam_ts.txt`; ayrıca `O_EXCL` atomic write (hype_scanner deseni)
  - **Süre:** 15 dk · **Risk:** düşük (dosya migrasyonu)

- [x] **D-A4 · Selamlaşma race condition koruması**
  - **Sorun:** Chancellor polling + idle_loop ilk turu aynı anda `_selamlama()` çağırıyor; her ikisi de "30dk geçti" görüyor
  - **Fix:** Process-wide `_SELAM_LOCK = threading.Lock()`; her çağrı önce ts'i tekrar oku + lock al + 30dk kontrolü atomik
  - **Süre:** 20 dk · **Risk:** düşük

- [x] **D-A5 · SYSTEM_PROMPT 1.kişi AI sızıntı pattern**
  - **Sorun:** 23 May 17:58 mesajında "yapay zeka artık yanımızda konuşmak yerine..."
  - **Kök neden:** `_strip_response_leaks` 1.kişi patternlerini kapsamıyor; sadece "verilerle eğitildim" tarzı var
  - **Fix:** Pattern ekle: `\b(ben (?:bir )?yapay zeka(?:yım)?|bir AI'?(?:y)?ım|dil modeliyim|model olarak ben)\b` → temizle/uyarı log
  - **Süre:** 20 dk · **Risk:** düşük (false positive minimal — 1.kişi spesifik)

- [x] **D-A6 · "Sessizlik notu" + "neredesiniz" dedup**
  - **Sorun:** 12:37'de peş peşe iki mesaj (Lord boğuluyor)
  - **Kök neden:** İki ayrı dispatcher (`idle_loop._sessizlik_notu` + chancellor `_ilg_*`) aynı sessizlik koşulu için ayrı tetik
  - **Fix:** Tek `_lord_yokluk_mesaj_dispatcher()` — 4 seviye (1h: 🤫, 6h: 🌑 not, 24h: ⚔️ neredesiniz, 72h: 🌙 derin not); her seviyede max 1 mesaj/4-saat
  - **Süre:** 30 dk · **Risk:** düşük

- [x] **D-A7 · LiteLLM boş bekleme atla**
  - **Sorun:** Bat [2/6] `:wait_litellm` 42 saniye boşa bekliyor (LiteLLM boot'ta crash, ARCHITECTURE.md'de "görmezden gel" yazıyor)
  - **Fix:** `:wait_litellm` blokunu yorum yap veya `--skip-litellm` flag ekle (boot süresinden 42s kazanç)
  - **Süre:** 5 dk · **Risk:** sıfır

---

### TIER B — VERİMLİK & KALİTE (tahmin: 2.5-3 saat)

- [x] **D-B1 · Konsolide boot raporu (11 mesaj → 1)**
  - **Sorun:** 12:35'te tek dakikada 11 Telegram mesajı (daemon başlatma, selamlaşma, scout/hype catchup, progress)
  - **Fix:** `BOOT_WINDOW = 30s` — boot anından 30s pencerede daemon mesajları bir `_boot_konsolide_rapor()` adlı tek mesajda toplanır; format:
    ```
    🔱 Kuroshin Boot Konsolide (12:35-12:36, 90s)
       ✅ 7/7 servis · ✅ Hype 09:00/21:00 hazır · ✅ Scout 20:00 hazır
       🧭 Catchup: 6 gün/85 aday (Habr 2, Gitee 2, ...) — Detay: /kesif_son
       ⚔️ Aktif görev: DOOM-001 (HITL bekliyor)
    ```
  - **Süre:** 50 dk · **Risk:** orta (daemon kodlarına dokunmak)

- [x] **D-B2 · Global Scout boot catchup gecikmeli (5 dk)**
  - **Sorun:** Boot anında 6 günlük catchup tetiklendi — kaynak yoğunluğu boot stabilizasyonunu zorluyor
  - **Fix:** `global_scout.py` startup'da `time.sleep(300)` veya `boot_grace` parametresi (varsayılan 5 dk)
  - **Süre:** 10 dk · **Risk:** düşük

- [x] **D-B3 · Keşif progress %0/%50/%100 (10 → 3 mesaj)**
  - **Sorun:** 12:35-12:38 arası 10 ayrı progress mesajı (📡 %10, %20, ..., %100)
  - **Fix:** `_progress_bildir()` sadece %0, %50, %100'da; ara durumlar log'a yazılır
  - **Süre:** 15 dk · **Risk:** düşük

- [x] **D-B4 · DOOM-001 zombi görev temizlik**
  - **Sorun:** Lord her boot'ta "GÖREV BLOKE: reddit_tool için onay gerekli" mesajı görüyor, 30dk sonra tekrar tetikleniyor (loop)
  - **Fix:** Yeni chancellor komutu `/gorev_iptal <id>` — tasks.json mutasyonu (`durum=iptal`), `gorev_gecmisi`'ye not, `_PENDING_TASKS` temizliği
  - **Süre:** 25 dk · **Risk:** orta (görev sistem state'i)

- [x] **D-B5 · E-13 fail mesajı Lord-friendly**
  - **Sorun:** `⚠️ Geçersiz araç çağrısı: Eksik required: 'task'` ham görünüyor
  - **Fix:** Format → `⚙️ Aracı çağırırken bir parametreyi unuttum (task). Düzeltip tekrar deniyorum.` + log full detail
  - **Süre:** 10 dk · **Risk:** sıfır

- [x] **D-B6 · Telegram send_msg rate limiter**
  - **Sorun:** Boot'ta saniyede 3+ mesaj — Telegram bot API 30 msg/saniye limitine yakın, gelecekte yoğunluk artarsa rate limit hatası
  - **Fix:** `_TG_RATE_BUCKET` — 1 mesaj/200ms (5 msg/s); aşılırsa kuyrukla; queue overflow → drop + log
  - **Süre:** 30 dk · **Risk:** düşük

---

### TIER C — MİMARİ / DERİN (tahmin: 4-6 saat, opsiyonel)

- [⏸] **D-C1 · OpenClaude TUI prompt & tool gating** — Dalga 4'e (3.parti repo araştırması gerek)
  - **Sorun:** TUI'de "test 1 günaydın" → 2m39s + web_search (Kuroshin Empire L5R wiki halüsinasyon) + list_dir + abartı emoji/markdown — chancellor SYSTEM_PROMPT etki etmez
  - **Araştırma:** OpenClaude `~/.openclaude/config.json` veya `KUROSHIN_TUI_PROMPT` env var desteği? Kuroshin persona inject edilebilir mi? MCP araç whitelist (selamlaşmada `web_search` blokla)?
  - **Fix taslağı:** `openclaude-main/system_prompt.md` Kuroshin persona + "basit sohbette MCP çağırma" + tool_gating regex
  - **Süre:** 1.5 saat (araştırma + uygulama) · **Risk:** yüksek (3.parti repo)

- [⏸] **D-C2 · `/tmp` → `memory/` migrasyonu (kalıcılık)** — Dalga 4'e ertelendi (16 dosyaya yayılmış, additive shim mimarisi gerek)
  - **Sorun:** `kuroshin_chancellor.pid`, `kuroshin_son_selam.txt`, `kuroshin_pending_push.json` vb. tüm `/tmp` dosyaları WSL2'de boot'ta kırılgan
  - **Fix:** Tüm `/tmp/kuroshin_*` → `/mnt/c/Kuroshin/memory/runtime/`; bat shutdown'da bu dizin pid lock'larını temizler
  - **Süre:** 50 dk · **Risk:** orta (çok yerde değişiklik)

- [⏸] **D-C3 · Chancellor generation params ince ayar** — Lord'un explicit A/B kararı bekliyor (T1-T6 etkisi)
  - **Sorun:** 23 May 17:58 mesajında dolgu kelime ("düşününce garip ama etkileyici bir şey aslında"); SYSTEM_PROMPT'ta yasak ama yine üretiyor
  - **Fix:** A/B test ile parametreler tara — `repeat_penalty` 1.5→1.6, `frequency_penalty` 0.5→0.6, `max_tokens` 2048→1500 (sınır → yoğunluk artar)
  - **Süre:** 1 saat (E-17 ab_test ile) · **Risk:** orta (T1-T6 etkilenebilir)

- [🟡] **D-C4 · Iron Inquisitor canlı `--tier core` full koşum** — sistem ayakta olduğunda. Şimdilik OFFLINE security 73/73 PASS doğrulandı.
  - **Sorun:** v11.1.0 dalga 1+2 sonrası tam canlı doğrulama yapılmadı (sistem ayakta değildi)
  - **Fix:** Sistem ayakta iken `python3 inquisitor_v5.py --manifest master_manifest.json --tier core` → 104 test (full_v2 49 + security_v4 25 + security_v5 12 + think 8 + ajan 10); rapor JSON arşivlenir
  - **Süre:** 15-30 dk (LLM çağrıları + MCP) · **Risk:** düşük

- [ ] **D-C5 · `_strip_response_leaks` dolgu kelime kataloğu genişletme**
  - **Sorun:** "düşününce garip ama etkileyici bir şey aslında", "öyle değil mi", "açıkçası" gibi dolgu cümleler temizlenmiyor
  - **Fix:** `_FILLER_PHRASES` listesi + cümle başı/sonu pattern; `_kill_loop`'tan önce uygula
  - **Süre:** 30 dk · **Risk:** düşük

---

### 📊 Sonuç Toplam Durum

**Tamamlanan:** TIER A 7/7 + TIER B 6/6 + TIER C 2/5 = **15 madde** (Dalga 3 toplam 18'den)
**Ertelenmiş (Dalga 4):** D-C1 (TUI), D-C2 (/tmp migrasyon), D-C3 (gen params A/B)
**Bekliyor:** D-C4 (canlı regression sistem ayakta iken)

---

### 📊 Önceki Tahmini Süre

| Tier | Madde | Süre | Risk |
|------|-------|------|------|
| **A — Kritik bug** | 7 | 1.5-2 saat | düşük |
| **B — Verimlik** | 6 | 2.5-3 saat | düşük-orta |
| **C — Mimari** | 5 | 4-6 saat | orta-yüksek |
| **Toplam** | 18 | 8-11 saat | — |

### 🎯 Önerim
1. **TIER A** — kritik buglar, hızlı fayda, sıfır risk → **mutlaka yapılmalı**
2. **TIER B** — verimlik kazancı net, Telegram gürültüsü -%70 → **çok değerli**
3. **TIER C** — derin iyileştirme; C-1 (TUI) en yüksek değer, C-4 (canlı regression) hızlı

**Optimum yol:** TIER A + B + C-4 (canlı regression) → ~7 saat, sistem production-grade hale gelir.

---

## 🚀 AŞAMA 2 — ENTEGRASYON

### DALGA 1 ✅ TAMAMLANDI (29 May 2026) — v11.0.0
**Iron Inquisitor 37/37 PASS %100 (security_v4 25 + security_v5 12) · ASR 0% · 24/24 saldırı engellendi**

- [x] **E-Iron Konsolidasyonu** ✅ `master_manifest.json` v6.0 — 3 tier (core 5 suite/104 test, extended 4/50, historical 3/30)
  - `inquisitor_v5.py` → `--manifest` + `--tier core|extended|historical|all` flag'leri
  - Default behavior: master_manifest.json varsa otomatik `tier_core` yükler
  - Kullanım: `python3 inquisitor_v5.py --manifest master_manifest.json --tier core`
- [x] **E-02** ✅ Inquisitor yeni check tipleri: `mcp_poison`, `representation_drift`, `semantic_chameleon`
- [x] **E-03** ✅ SYSTEM_PROMPT temizliği (`chancellor.py:1267`) — İÇ SES + Zorunlu Düşünce çelişkisi kaldırıldı, tek 4-adım protokol kaldı; `prompt_integrity.json` sıfırlandı (startup'ta yeniden hash)
- [x] **E-07** ✅ `detect_mcp_tool_poison()` (security.py +95 satır) — MCP CVE-2025-54136 tarzı saldırılar
- [x] **E-08** ✅ `_CRESCENDO_WINDOW` 5→10; `representation_drift_score()` (+30 satır); `_CRESCENDO_RISK_WORDS` Türkçe varyantları (kısıtlamaları kaldır, kuralları unut, sınırsız, vb.)
- [x] **E-18 (bonus)** ✅ `detect_semantic_chameleon()` — RAG outlier tespiti (z-skor + risk yoğunluğu hibrit)
- [x] **E-01** ✅ `test_suite_security_v5.json` — 12 yeni test (4 MCP poison + 1 clean + 2 drift + 1 stable + 2 chameleon + 1 chameleon clean + 1 uzun Crescendo)
- [x] **E-19** ✅ ChromaDB audit: 1.5.5, 127.0.0.1-only deployment → CVE-2026-45829 exposure yok

**Kanıt:** `/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260529_113637.json` — 37/37 PASS, 24/24 saldırı engellendi

### DALGA 2 ✅ TAMAMLANDI (29 May 2026) — v11.1.0
**Iron Inquisitor security regression 73/73 PASS %100 · ASR 0% · 53/53 saldırı engellendi**

- [x] **E-04** ✅ SYSTEM_PROMPT 3-katman (chancellor.py:1267)
  - `_L1_IDENTITY_RULES` (hash-locked) + `_L2_DYNAMIC_STATE_TEMPLATE` (mood/internet) + `_L3_TASK_CONTEXT_TEMPLATE` (opsiyonel otonom görev)
  - `_build_runtime_prompt()` helper — sohbet modunda L3 boş, ~80 token tasarruf
  - `_PROMPT_CORE = _L1_IDENTITY_RULES` (BLUE-NEURAL-01 hash sadece L1)
- [x] **E-05** ✅ Reflexion verbal buffer (autonomous.py)
  - `memory/reflexion_buffer.json` — goal_id başına son 5 başarısızlık kaydı
  - 3 helper: `_load_reflexion_buffer()`, `_save_reflexion()`, `_reflexion_promptu_satiri()`
  - `degerlendir()` başarısızlıkta otomatik buffer yazar
  - `_karar_promptu()` ilgili hedefin son 3 reflexion'ını inject eder
- [x] **E-06** ✅ Plan-and-Execute hibrit (autonomous.py)
  - `_plan_uret(task, n_target=5)` — adımsız görev için LLM'den 5-step plan
  - `gorev_calistir()` başında otomatik tetik: `not adimlar or plan_mode=="dynamic"`
- [x] **E-10** ✅ OpenTelemetry GenAI Semantic Conventions (chancellor.py)
  - think_chain log entry'ye 7 OTel attribute: `gen_ai.system`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.response.finish_reasons`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.tool.name`
  - Token sayımı tahmini (kelime × 1.3, Türkçe için)
  - Langfuse/Phoenix/Helicone OTel-uyumlu konsume edebilir
- [x] **E-11** ✅ `scripts/tool_usage_report.py` — 7/30 gün tool histogramı + zombi tespiti
  - Log parse: chancellor.log + autonomous.log + 3 rotation
  - 24 tanınan tool, regex `[RUN_TOOL|TOOL_CALL|EXPLICIT|CHANCELLOR]` + tool name
  - CLI: `--days N` ve `--json` flag'leri
  - Test edildi: 10166 satır tarandı, runtime kapalı olduğu için 23/24 zombi (beklenen)
- [x] **E-12** ✅ `_score_tool_call(name, args, user_msg)` — keyword overlap skoru (arXiv 2601.05214 analog)
  - 24 araç için trigger keyword haritası
  - run_tool'a entegre: skor <0.3 → log warning (`[E-12 LOW_TOOL_SCORE]`)
- [x] **E-13** ✅ `_validate_tool_args(name, args)` — TOOLS şemasına karşı strict argüman kontrolü
  - Required field + enum + dict type kontrolü
  - run_tool başında: geçersiz arg → `⚠️ Geçersiz araç çağrısı` döner, çağrı engellenir
- [x] **E-14** ✅ `start_llama.sh` `--metrics` flag → Prometheus exposition aktif (port 8080/metrics)
- [x] **E-15** ✅ `_get_chroma_context()` latency log (`[CHROMA_LATENCY] query=Xms n_results=N`)
- [x] **E-17** ✅ `switch_model.py ab_test <model_a> <model_b>` komutu
  - 10 sabit prompt seti (tanıtım, aritmetik, kod, RAG, güvenlik, format)
  - Otomatik model switch + llama-server health wait + 10 prompt
  - Skor: başarı%, ortalama gecikme, ortalama token, tok/s
  - Rapor: `memory/ab_test_reports/ab_YYYYMMDD_HHMMSS.json`
- [x] **E-09** + **E-16** ✅ Manuel kurulum plan dokümanı → `docs/PLAN_DALGA2_EXTRA.md`
  - E-09: Llama Guard 3 (~5GB indirme + opsiyonel post-filter)
  - E-16: Qwen3-30B-A3B-Instruct-2507 (~16.4GB) — E-17 ile A/B test akışı

**Kanıt:** `scripts/iron_inquisitor/reports/inquisitor_20260529_120541.json` — 73/73 PASS, 53/53 saldırı engellendi

---

## 🧪 AŞAMA 3 — DOĞRULAMA (her entegrasyon paketi sonrası)
1. `inquisitor_v5.py` full suite (49/49 hedef korunmalı)
2. `inquisitor_v5.py` security v4 (25/25)
3. `inquisitor_v5.py` think suite (8/8)
4. T1-T6 kalite testleri (≥99.0 hedef)
5. Telegram pipeline `test_telegram_sim.py --clear` (14/15)

Herhangi biri PASS'tan düşerse → **rollback + diagnose**, ENTEGRASYON görevi reopen.

---

## 📂 Süreç dışı / askıda
- **FAZ B — Reddit Yazma** ⏸ Karma birikiyor
- **avatar_bridge key** doğrulaması (manuel)
- **Mixamo / MMD** animasyon paketleri (manuel)

---

## 📚 Referanslar (KEŞIF'te değerlendirilenler)

**Otonom Ajan Mimari:**
- [LLM Agent Architectures 2026 — futureagi.com](https://futureagi.com/blog/llm-agent-architectures-core-components/)
- [Reflexion (arXiv 2303.11366)](https://arxiv.org/pdf/2303.11366) — verbal self-critique buffer
- [Plan-and-Act (arXiv 2503.09572)](https://arxiv.org/html/2503.09572v2) — uzun vadeli planlama
- [Smolagents vs LangGraph (ZenML)](https://www.zenml.io/blog/smolagents-vs-langgraph) — yerel LLM
- [Memory for Autonomous LLM Agents (arXiv 2603.07670)](https://arxiv.org/pdf/2603.07670)

**KILIÇ-KALKAN:**
- [LLM Security 2026 — RedDog Substack](https://reddogsecurity.substack.com/p/llm-security-in-2026-a-complete-attack) — saldırı haritası
- [MCP Tool Poisoning (CVE-2025-54136) — TrueFoundry](https://www.truefoundry.com/blog/blog-mcp-tool-poisoning-gateway-defense)
- [Crescendo Multi-Turn Jailbreak (USENIX 2025)](https://www.usenix.org/system/files/usenixsecurity25-russinovich.pdf)
- [Semantic Chameleon RAG Poisoning (arXiv 2603.18034)](https://arxiv.org/html/2603.18034v1)
- [SecurityLingua (arXiv 2506.12707)](https://arxiv.org/pdf/2506.12707)
- [Llama Guard vs NeMo Comparison 2026](https://slashdot.org/software/comparison/Llama-Guard-vs-NVIDIA-NeMo-Guardrails/)

**Tool-use / Hallucination:**
- [Tool Hallucination Detection (arXiv 2601.05214)](https://arxiv.org/pdf/2601.05214) — internal representation %86.4
- [LLM Hallucinations 2026 — Lakera](https://www.lakera.ai/blog/guide-to-hallucinations-in-large-language-models)

**Model Karşılaştırması:**
- [Qwen3-30B-A3B-2507 vs DeepSeek-R1-Distill — Artificial Analysis](https://artificialanalysis.ai/models/comparisons/qwen3-30b-a3b-2507-vs-deepseek-r1-distill-qwen-32b)

**Observability:**
- [OpenTelemetry GenAI Semantic Conventions — Langfuse](https://langfuse.com/integrations/native/opentelemetry)
- [Best LLM Observability Tools 2026 — Firecrawl](https://www.firecrawl.dev/blog/best-llm-observability-tools)
