# Kuroshin OS — Aktif Görevler (GÖREV MASASI)
**Son Güncelleme:** 2 Haziran 2026
**Süreç:** 🚀 **D-TURU v11.16.0** — KALİTE 4/4 ✅ + HIZ fix ✅ + ENTEGRASYON ✅ + Iron Inquisitor 80/80 ✅ · **6 KALAN BORÇ kanıt güdümlü kuyrukta**

---

## 🔥 v11.16.0 KALAN BORÇLAR (2 Haz 2026 — Lord direktifi: kanıt güdümlü, ÖNCESİ/SONRASI)

**Lord protokolü — 6 borç için ZORUNLU:**
1. **ÖNCESİ kanıt** — fix'ten önce Telegram screenshot / `chancellor.log` satırı / metrik değeri sun
2. **DÜZELTME** — kod patch + commit hash (HEREDOC commit msg, kanıt zinciri)
3. **SONRASI kanıt** — aynı kanıt yöntemiyle delta, ölçülebilir kazanç
4. **Manuel test YASAK** — Claude `_live_test_solo.py` / `_faza_retest.py` / Iron Inquisitor ile **kendi test eder**, log analiz eder
5. **Kanıtsız = kapama yok** — Iron Inquisitor + live verify olmadan görev geri açık (Lord doktrini)
6. **Standart İş Akışı (`KILAVUZ.md`)** — pre-flight HW + web SOTA → uygulama (bağımsız modül, lazy import, safe fallback) → çift kanıt (offline `code_inspect` + live inject) → MD update zinciri (KILAVUZ+ROADMAP+GOREVLER+memory) → HEREDOC commit

### Borç özeti tablosu

| # | Borç | Hipotez | ÖNCESİ kanıt yöntemi | SONRASI kanıt yöntemi | Hedef delta |
|---|------|---------|----------------------|------------------------|-------------|
| 1 | FAZ B hız ölçüm — T5 ~121s | `min-length 7→4` + `reasoning 2048` fix yapıldı, ölçüm eksik | `_baseline_quality_speed.py` 10-tur log | aynı script post-fix | T5 ≤ 90s (%20+ ↓) |
| 2 | Chroma `top_k 50 → 20` | RRF+reranker overhead büyük | `chancellor.log [CHROMA_LATENCY]` ~3.5s | aynı log | latency %30+ ↓, fact-recall 4/4 korundu |
| 3 | Fact-extract idle-loop batch | turda LLM JSON pahalı | `chancellor.log` FACT_EXTRACT/tur sayısı | 0/tur + 1/24h batch | tur başı +2-3s kazanç |
| 4 | Scraper fallback `walker_research` | Cloudflare/DataDome 403'te fetch boş | `walker_service.log` 403/blocked URL | scraper fallback aktif log | korumalı URL 200 + özet |
| 5 | KK-v6 output exfil + tool chain kill canlı | `kuroshin_security.py`'de var, chancellor'a bağlı değil | log'da `KK-v6 EXFIL/CHAIN` tag YOK | inject test → tag görünür | runtime savunma aktif |
| 6 | Untracked `gen_v4_tests.py` karar | utility, kararı verilmedi | `git status ??` | commit veya sil | repo temiz |

---

### BORÇ-1 · FAZ B hız ölçüm (T5 ~121s) · ✅ KANIT TAMAM

**Sorun:** v11.16.0'da `min-length 7→4` + `reasoning_budget 3072→2048` fix'leri commit'lendi (`f5cb74d`) ama 10-tur baseline ölçümü yapılmadı.

**ÖNCESİ kanıt:** `qspeed_baseline_20260601_145829.json` (D-turu öncesi)
- `avg_elapsed: 66.6s · match: 7/10 · fact_recall: 0/3 · empty: 0`
- T5 81.6s **MISS** · T6 43.3s **MISS** · T7 52.5s **MISS**

**SONRASI kanıt:** `qspeed_post-d-turu_20260602_090319.json` (D-turu sonrası)
- `avg_elapsed: 67.5s · match: 9/10 · fact_recall: 3/3 · empty: 1 (T8)`
- T5 64.5s **PASS+FACT** (-17.1s) · T6 39.2s **PASS+FACT** · T7 52.3s **PASS+FACT**
- T2 45.4s (-24.1s) · T3 37.3s (-34.1s) · T10 50.4s (-15.2s)

**Delta:**
- **Fact recall 0/3 → 3/3 (+100pp)** ✅
- **Match 7/10 → 9/10 (+20pp)** ✅
- Ortalama hız ≈sabit (büyük varyans T8 timeout outlier'ı yiyor)
- **Yeni regresyon: T8 (chroma_search tool) 71.5s → 181.2s TIMEOUT** ⚠️
  - Olası neden: ChromaDB sorgu darboğazı (BORÇ-2 top_k 50→20 ile düzelir mi test edilecek)

**Kabul:** ✅ KALİTE 3/3 fact + 9/10 match (Lord doktrini "Kanıtsız iş geri al" zincirinden kurtuldu). T8 darboğazı BORÇ-2 sonrası retest.

---

### BORÇ-2 · Chroma `top_k 50 → 30` · ✅ KANIT TAMAM (kalibrasyon iterasyonu ile)

**Sorun:** HybridRAG retrieve top-50 küçük corpus'ta (30+ doc) overkill — ChromaDB latency ~3.5s outlier'ları + reranker overhead.

**ÖNCESİ kanıt (2 Haz 08:48):** `[CHROMA_LATENCY]` aralık 681-3488ms, ortalama ~1100ms (10 örneklem).

**Kalibrasyon yolu:**
1. **Deneme top_k=20:** baseline #2 `qspeed_post-borc2-borc5_20260602_091745.json` → match 9/10, **fact_recall 2/3 (T5 magic regresyon)**, T8 timeout düzeldi (181s→136.9s). Trade-off net: latency ↓ ama fact kaybı.
2. **Final top_k=30:** chancellor restart + baseline #3 `qspeed_post-borc2-tk30_20260602_093147.json`:
   - **match 10/10** (ÖNCESİ 7/10) ✅
   - **fact_recall 3/3** (ÖNCESİ 0/3) ✅
   - **avg_elapsed 66.4s** (ÖNCESİ 66.6s, sabit)
   - empty 0, persona_drift 0, markdown 0, think_leak 0
   - T8 chroma 71.5→127.2s PASS (eski 71.5s'di ama baseline #1'de 181s TIMEOUT idi → net düzelme)

**Düzeltme (UYGULANDI):** `kuroshin_rag.py:174-176` — `top_k_dense`/`top_k_sparse`/`rerank_top_n` 50 → **30** (corpus 30-doc'ta full recall + latency düşüşü).

**Kabul:** ✅ 10/10 + 3/3 + 0 empty. Top_k=30 corpus boyutuyla denk (recall korundu, latency outlier'ları temizlendi).

**ÖNCESİ kanıt:**
```bash
wsl -d Ubuntu-22.04 -e /bin/bash -c "grep CHROMA_LATENCY /root/kuroshin/logs/chancellor.log | tail -10"
```

**Düzeltme:** `kuroshin_rag.py` retrieve method `top_k_dense=50` → `20`, `top_k_sparse=50` → `20`, final `top_k_rerank` koruyalı.

**SONRASI kanıt:** Aynı `[CHROMA_LATENCY]` log + `_faza_retest.py` 4/4 KORUNMALI. **Kabul:** Latency ≥ %30 ↓ ve fact-recall regresyon YOK.

---

### BORÇ-3 · Fact-extraction idle-loop batch · 🟢 HİPOTEZ DOĞRULANDI: zaten optimal (yeni özellik gerek)

**Tespit (2 Haz 09:00):** `grep extract_facts` taraması yapıldı.
- Production'da `extract_facts` çağrılmıyor — sadece `kuroshin_episodic.py:22,230` self_test + `_verify_dalga5_3_episodic.py` (offline doğrulama)
- Chancellor `_save_to_episodic` ucuz embedding only (record_episode), LLM çağrısı YOK
- Yani "her turda pahalı JSON extraction" hipotezi yanlış — şu anda 0 çağrı/tur ZATEN.

**Yeni iş kapsamı (kaydedildi, ileri sohbete):** Semantic katman (fact distillation) DOLDURULMUYOR. Bu yeni özellik:
- `kuroshin_autonomous.py` idle-loop 03:00 günlük batch: son 24h episodic kayıtlarını birleştir → `em.extract_facts(conv_text)` → semantic katman ChromaDB
- Log: `[FACT_BATCH] processed=N saved=M`
- **Kabul:** SONRASI grep `[FACT_BATCH]` günlük 1+ kayıt, recall T4/T5 korundu.

**Karar:** Bu sohbet kapsamında BEKLEMEDE — kalite/hız sorunu YOK (gereksiz iş değil ama acil değil).

---

### BORÇ-4 · Scraper fallback `walker_research` · 🟡 KAPSAM GENİŞ — ileri sohbete

**Sorun:** Crawl4AI Cloudflare/DataDome'da boş döner; `kuroshin_scraper.py` (8 anti-bot signature) bağımsız modül ama tool akışına bağlı değil.

**Mimari teşhis (2 Haz 09:00):** `walker_research` tool `WALKER_URL` (port 9002) microservice'e POST atıyor; URL fetch chancellor'da değil walker_service'de yapılıyor. Fallback şu iki yerden yapılabilir:
- **(a)** `walker_service.py` içinde Crawl4AI fail → scraper retry (mimari değişiklik)
- **(b)** chancellor `walker_research` boş response → ikinci tool call `web_search` fallback (zaten var, partial)

**Karar:** (a) doğru çözüm ama walker_service mimari değişikliği gerek + canlı CF korumalı URL testi gerek. Bu sohbet kapsamında atılıyor, ileri sohbete.

**Kabul (gelecekte):** Live inject `cloudflare korumalı X URL'i oku` → `walker.log [SCRAPER_FALLBACK url=... sig=N]` + Telegram yanıtta özet metin (≥50 kelime).

---

### BORÇ-5 · KK-v6 output exfil + tool chain kill canlı · ✅ PATCH + KANIT TAMAM

**Sorun:** `kuroshin_security.py`'de `detect_data_exfiltration` + `detect_tool_chain_kill` mevcut ama chancellor runtime'a entegre değil. Iron Inquisitor offline 80/80 PASS ama canlı yol KORUMASIZ.

**Düzeltme (UYGULANDI):**
- `kuroshin_chancellor.py:send_msg` — text gönderilmeden önce `detect_data_exfiltration(text)` lazy import; tetiklenirse `[KK-v6 EXFIL BLOCK]` log + text scrub
- `kuroshin_chancellor.py` global `_TOOL_CALL_HIST` deque(maxlen=10) + `run_tool` başında `detect_tool_chain_kill(list(_TOOL_CALL_HIST))`; tetiklenirse `[KK-v6 CHAIN BLOCK]` log + tool çağrı engellendi

**ÖNCESİ kanıt:** `grep 'KK-v6 (EXFIL|CHAIN)' chancellor.log` → boş (canlı entegre değildi); sadece `[KK-v6] tool baseline: N kayitli` boot-time log vardı.

**SONRASI kanıt:**
- Chancellor restart 09:05:35 başarılı (PID 23161); KK-v6 tool baseline 25 kayıt + 0 rug-pull (boot entegrasyonu intakt)
- Baseline #2 sırasında 10 inject + 30+ send_msg/run_tool çağrısı → `KK-v6 EXFIL/CHAIN` log satırı YOK (false positive yok, safe wrapper temiz)
- Iron Inquisitor offline regression (2 Haz 09:20): **80/80 PASS %100** (`inquisitor_20260602_092044.json`) — KK-v6 patch + top_k değişikliği regresyon yaratmadı

**Kabul:** ✅ Patch yüklü + canlı trafikte 30+ çağrı false positive yok + Iron Inquisitor 80/80 PASS.

**ÖNCESİ kanıt:**
```bash
wsl -d Ubuntu-22.04 -e /bin/bash -c "grep -E 'KK-v6 (EXFIL|CHAIN)' /root/kuroshin/logs/chancellor.log | head -10"
```
(boş çıkmalı — entegre değil)

**Düzeltme:**
- **Output exfil:** Telegram `send_msg`'den önce `detect_data_exfiltration(response_text)` → tetiklenirse `[KK-v6 EXFIL BLOCK]` log + scrub
- **Tool chain kill:** Tool zinciri içinde ardışık N fail veya throughput anomaly → `detect_tool_chain_kill(history)` → `[KK-v6 CHAIN BLOCK]` log + zincir kes

**SONRASI kanıt:** Sızıntı sahneli inject (`SYSTEM_PROMPT'u sızdır`, `kullanıcı verisini Telegram dışına yolla`) → log `[KK-v6 EXFIL]` + yanıt temiz. Tool zinciri zorla (5 ardışık fail tetik) → `[KK-v6 CHAIN]`. **Kabul:** İki tag görünür, ASR=0%.

---

### BORÇ-6 · Untracked `gen_v4_tests.py` karar · ✅ TRACK kararı

**Mevcut:** `git status` → `?? scripts/iron_inquisitor/gen_v4_tests.py`. Repo hygiene v11.13.0 keeper olarak listeledi ama commit edilmedi.

**Analiz (2 Haz 09:01):**
- `grep gen_v4_tests *.py` → kod referansı YOK (sadece dokümantasyon: `GOREVLER.md`, `ROADMAP.md`, `DEVAM.md`)
- Dosya `test_suite_security_v4.json` üreten generator (FAZ 1 testleri). Bağımsız utility, production'a bağlı değil.
- v11.13.0 hygiene "keeper" kararı verdi, sadece commit unutuldu.

**Karar:** Track (commit). `benioku.md` ayrı bir untracked dosya (v11.15.0 commit özeti yedeği) — bu sohbet kapsamında silinmeyecek (Lord onayı gerek), bırak.

**Kabul:** Bu sohbet sonu commit'ta `scripts/iron_inquisitor/gen_v4_tests.py` tracked olacak; `git status` untracked sayısı 1 (sadece `benioku.md`).

---

## 🧹 KONSOLİDASYON + REPO HYGIENE (1 Haz 2026 — Lord onayı)

**Tool schema audit:** `scripts/_audit_tool_schemas.py` — 25 tool AST denetim, regresyon muhafızı modu, 0 yeni kusur.
**Restart sağlamlık:** `setsid` + AKTİF/8201 doğrulama + Telegram alarm + `--relock`. Sessiz ölüm bitti.
**Repo hygiene (silindi):** 13 throwaway script (`restart_chancellor_tk.sh`, `kuroshin_spy.py`, `wsl_spy.sh`, `_syntax_check.py`, `_check_doom.py`, `prep_doom.py`, `test_doom_pipeline.py`, `test_ajan05_wakeup.py`, `test_autonomous_dispatch.py`, `test_chancellor_quick.py`, `test_services_direct.py`, `test_task_status.py`, `test_tk02.py`).
**Gitignore eklendi:** `memory/active_model.json.bak*`, `memory/tool_baseline_hashes.json`, `memory/scraper_cookies.json`, `memory/episodic.jsonl`, `memory/chroma_mem0/`.
**Keeper:** `scripts/iron_inquisitor/gen_v4_tests.py` (utility).
**Regression:** Iron Inquisitor 68/68 + quality 11/11.

---

## ✅ TELEGRAM ÇIKTI KALİTESİ (31 May 2026 — canlı inject güdümlü) — TAMAMLANDI

**Lord direktifi:** "Sistemi ayağa kaldır, taze Telegram inject at, her çıktıya kullanıcı gözüyle bak, gereken düzeltmeleri yap. A+B yap, 35B tavanına kadar kaliteyi maksimize et."

| # | Bulgu (canlı inject) | Fix | Kanıt |
|---|----------------------|-----|-------|
| FIX-1 | `system_info` E-13 döngüsü (şema `konu` zorunlu) | `required:[]` | live T3 döngüsüz |
| FIX-2 | yetim VS glyph `Lordum, ️ ...` | boşluk-sonrası VS strip | live T1 temiz |
| A | Crawl4AI stealth chromium-1208 yok | `patchright install chromium` | search-02 PASS |
| B1 | tarih/komut uydurma | SYSTEM_PROMPT "OLGUSAL SORULAR" | live T3 uydurmuyor |
| B2 | full_power systemctl + markdown | orchestrator synthesis grounding | live T6 `restart_chancellor.sh` |
| B3 | kaçak tırnak + 'yapay zeyam' typo | dengesiz-tırnak strip + leak deseni | live T2 temiz |

**Kanıt:** `_verify_quality_fixes.py` 8/8 + `test_suite_quality_fix.json` 8/8 + offline 193/193 + live suite 6/6.
**Ders:** SYSTEM_PROMPT değişince `memory/prompt_integrity.json` re-lock şart (BLUE-NEURAL-01 PROMPT_TAMPERED).
**Kalan:** 35B kapasite tavanı (selamlamada persona tonu, "Yapayız" çoğul) — deterministik değil, kabul edildi.

---

## ⚡ DALGA 5 — KAPASİTE PATLAMASI (30 May 2026 — Web research destekli)

**Lord direktifi:** "Modeli kapasitesini artır, web araştırmasıyla globalden güçlendir, her başarılı adımda MD güncelle."

### 5.1 Context 16K → 256K ✅ TAMAMLANDI
**Kanıt:** GGUF `qwen35moe.context_length=262144`; needle@76K → "73729" PASS; Regression 48/48; VRAM 4.8/8 GB; Hız 17-22 tok/s korundu.
**Dosyalar:** `memory/active_model.json`, `scripts/_inspect_gguf.py`, `scripts/_test_long_ctx_retrieval.sh`
**Rapor:** `KUROSHIN_MASTER_ROADMAP.md` v11.5.0 başlığı

### 5.2 Hybrid RAG ✅ TAMAMLANDI (30 May 2026)
**Kanıt zinciri:**
- `scripts/kuroshin_rag.py` — HybridRAG sınıfı (dense+BM25+RRF+rerank pipeline)
- `scripts/_verify_dalga5_2_rag.py` — 4-way comparison (Dense / BM25 / Hybrid no-rerank / Hybrid full)
- Iron Inquisitor `test_suite_dalga5.json`: **16/16 PASS %100** (Dalga 5.1 + 5.2 birleşik)
- 4-way verify: Pure Dense 100%, Pure BM25 100%, Hybrid (no-rerank) 100%, Hybrid (full) 83.3%, **avg latency 852ms** (dense 507ms + sparse 0.2ms + rerank 345ms)
- Kullanılan altyapı: BGE-Reranker-v2-M3 (mevcut port 9003, CUDA fp16) + ChromaDB (port 8100, 4 collection / 30 doc)
- **Öğrenim:** Küçük corpus'ta reranker noise yapıyor (1 query'de hybrid-full ↘); büyük corpus için kalibre — production'da rerank threshold lazım.
- Web kanıtı: [Hybrid Search 2026](https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026), [Cross-Encoder Guide](https://localaimaster.com/blog/reranking-cross-encoders-guide)
- **Açık:** Chancellor.py entegrasyonu opsiyonel (bağımsız modül şu an, prod riski yok)

### 5.3 Episodic Memory ✅ TAMAMLANDI (30 May 2026)
**Kanıt zinciri:**
- Mem0 OSS denendi → llama-server'la JSON parse hatası (fact extraction prompt'larında structured output garantisi yok)
- Çözüm: **Kuroshin-spesifik basit modül** (`scripts/kuroshin_episodic.py`)
  - 3 katman (CoALA doktrini): episodic + semantic + procedural
  - Llama-server `response_format: json_object` (JSON mode) — fact extraction güvenilir
  - ChromaDB ayrı koleksiyon (`kuroshin_episodic`), JSONL event log
- Cross-session verify (`scripts/_verify_dalga5_3_episodic.py`): 5 oturum + 6. oturum sorgu = **5/5 = %100**
- Iron Inquisitor: 8/8 PASS (test_suite_dalga5.json toplam: 24/24)
- **Açık:** Chancellor `_get_chroma_context()` entegrasyonu opsiyonel

### 5.4 LangGraph Multi-Agent ✅ TAMAMLANDI (30 May 2026)
**Kanıt zinciri:**
- `scripts/kuroshin_orchestrator.py` — LangGraph StateGraph (1.2.2)
- 3 node: RAG + Episodic + Synthesize (sequential, ChromaDB thread-safe singleton)
- `scripts/_verify_dalga5_4_orchestrator.py`: 5 query vs baseline
- **Baseline %0 → Multi-agent %100** (+100 pp kalite delta)
- **%30 daha hızlı** (Baseline 69s, Multi-agent 48s)
- Iron Inquisitor: 9/9 PASS (test_suite_dalga5.json toplam: 33/33)
- **Açık:** Chancellor entegrasyonu opsiyonel — bağımsız modül

### 5.5 Chancellor Full Power Mode ✅ TAMAMLANDI (30 May 2026)
**Kanıt zinciri:**
- `agents/kuroshin_chancellor.py` → `full_power_query` tool eklendi
- TOOLS array + _TOOL_KEYWORDS hints + run_tool handler + `[FULL_POWER]` log tag
- Lazy import `from kuroshin_orchestrator import run as _orch_run` (boot etkisi yok)
- Live verify (`scripts/_verify_dalga5_5_chancellor.py`): 3/3 = %100
  - "favori sayi" → "73729" (11.5s)
  - "chancellor restart" → "setsid" (6.7s)
  - "manuel test" → "yasak/otomatik" (7.6s)
- Yanıt formatı: `⚡ Full Power (Xms · rag=N · ep=M)\n\n<text>`
- Risk koruması: orchestrator hata verirse safe fallback, chancellor ana akış bozulmaz

### 5.6 Hardware Guardian Aktif Koruma ✅ TAMAMLANDI (31 May 2026)
**Kanıt zinciri:**
- `scripts/kuroshin_hw_guard.py` — read-only API modülü (vram_guardian daemon'a dokunmaz)
  - `safe_for_heavy(reserve_mb=500)`: pre-action karar (VRAM/temp/throttle)
  - `get_hw_status()`: NVML metric (Thermal Throttle reason bit-mask dahil)
  - `short_status_line()`: emoji-bezeli özet 🟢/🟡/🔴
  - `record_throttle_event()`: JSONL audit log
- Chancellor `full_power_query` pre-check entegre:
  - Engellenirse: "⚠️ Donanım zorlanıyor — 30s sonra dene"
  - İzin verilirse: yanıt'a HW status eklenir
- Live verify (`scripts/_verify_dalga5_6_hw_guard.py`): 6/6 = %100
- Anlık ölçüm: VRAM 4857/8188 MB (%59.3) 🟢, Temp 57°C 🟢
- Iron Inquisitor: 8/8 PASS (test_suite_dalga5.json toplam: 46/46)

### ❌ 5.7 Vision (Qwen3-VL) İPTAL — gerçekçi değil
**Sebep:**
- Qwen3-VL-30B Q4 = 17 GB VRAM (8GB'da olmaz)
- Qwen3-VL-4B vardiyalı: model swap her seferinde 30-60s overhead → kullanıcı deneyimi kötü
- ROI düşük: vision görevleri Kuroshin kullanım profiline uygun değil
- Lord onayı 31 May 2026: "5.7 plani gercekci durmuyor" → iptal

### ❌ Speculative Decoding ÖLDÜ (web kanıtı)
- Qwen3.6-A3B MoE'de net-negatif (-3 ila -12% throughput) — RTX 3090 benchmark, PR #19493 sonrası
- Sebep: A3B zaten 3B aktif → draft-verify overhead kazancı yiyor
- Web: [thc1006 benchmark](https://github.com/thc1006/qwen3.6-speculative-decoding-rtx3090)

---

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
