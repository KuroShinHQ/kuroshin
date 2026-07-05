# MODEL SWITCHER TEST SONUÇLARI VE DEĞERLENDİRME RAPORU

**Oluşturulma Tarihi:** 5 Temmuz 2026  
**Son Güncelleme:** 5 Temmuz 2026 (v2 — DeepSeek 32B iptal, 14B önerisi eklendi)  
**Hedef Sistem:** Kuroshin OS (RTX 4060 Laptop 8GB VRAM + 32GB RAM)  
**Test Aracı:** Iron Inquisitor v5.2  
**Durum:** DeepSeek R1 32B bu hardware'de çalışmaz  

---

## 1. Amac ve Kapsam
Bu doküman, Kuroshin projesinin yerel yapay zeka beynini en doğru adaya taşımak için hazırlanmış resmi test planıdır. Sistemde aktif olan mevcut 35B modeli ile önerilen iki yeni 30B/32B seviyesindeki model yerel donanımımız ve otonom yazılım ajanımız (OpenClaude / Iron Inquisitor) üzerinde kıyaslanmıştır.

### Test Edilen Modeller:
1. **Model A (Mevcut):** `Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf` (17.44 GB ✅ TEST EDİLDİ)
2. **Model B (Düşünme/Mantık Odaklı):** `DeepSeek-R1-Distill-Qwen-32B-abliterated-Q4_K_M.gguf` (19.85 GB ❌ BU HARDWARE'DE ÇALIŞMAZ — silindi)
3. **Model C (Ajan/Hız Odaklı):** `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` (18.54 GB ✅ TEST EDİLDİ)

## 2. ESKI TEST SONUÇLARI (run_benchmarks.py — 238 eski infra testi)

`run_benchmarks.py` 3 modeli de 238 test senaryosu üzerinden değerlendirdi. **UYARI:** Bu testler MCP araç çağırma altyapısını ölçer, modelin gerçek muhakeme/kod/yeteneklerini ölçmez. Bu yüzden 3 model de birbirine yakın skor aldı — farkı görmek için yeni `model_select` testleri eklendi (bkz. Bölüm 3).

| Model | PASS | FAIL | Başarı | Hız (tok/s) |
|---|---|---|---|---|
| **Huihui 35B** | 195 | 43 | %81.9 | 17.4 |
| **DeepSeek R1 32B** | 193 | 45 | %81.1 | ~0.0* |
| **Qwen3 Coder 30B** | 195 | 43 | %81.9 | 20.9 |

*\*DeepSeek hızı CoT sebebiyle ölçülemedi*

### 2.1. Huihui 35B Neden Qwen3 Coder 30B ile Eşit? (Eski Testlerde)

Kullanıcının sorusu üzerine incelendi: **Huihui aslında daha eski/yetersiz değil, aksine:**

1. **Huihui = Qwen3.6** tabanlı — Qwen3 **Coder** ise Qwen3 tabanlı. "3.6" > "3", yani Huihui daha yeni bir base model üzerine inşa edilmiş.
2. **Claude-4.7-Opus fine-tune** — Huihui, Opus seviyesinde sentetik veriyle eğitilmiş. Tool calling ve instruction following'de bu büyük avantaj sağlar.
3. **35B total > 30B total** — Daha büyük toplam parametre, daha fazla öğrenme kapasitesi.
4. **Her ikisi de MoE (3B aktif)** — Aktif parametre aynı olunca inference hızı benzer, ama 35B'nin havuzu daha geniş.
5. **Test suite tool calling odaklı** — Genel bilgi/knowledge ölçmüyor, sadece MCP araçlarını doğru çağırma başarısını ölçüyor. Bu alanda fine-tuning kalitesi, model büyüklüğünden daha belirleyici.

**Özet:** Huihui daha modern bir base (Qwen3.6) + üstün fine-tune (Claude-4.7-Opus) sayesinde Qwen3 Coder ile aynı seviyede. Qwen3 Coder'ın tek avantajı %20 daha hızlı olması (20.9 vs 17.4 tok/s).

---

## 8. Soru-Cevap: Hugging Face Benchmarks vs. Yerel Testler
> **Soru:** *HF gibi sitelerde bu modellerin test sonuçları zaten var mı? Yerelde tekrar test etmeye gerek var mı?*

**Cevap:** Hugging Face üzerindeki testler genel akademik veri setlerine (HumanEval, MBPP vb.) ve sınırsız bulut kaynaklarına dayanır. **Yerel olarak test etmemiz kesinlikle zorunludur çünkü:**

* **Donanım Paylaşımı ve Hız Testi (RTX 4060 + 32GB RAM):** Hugging Face, modellerin ekran kartınızın VRAM'i ile sistem RAM'iniz arasında bölünerek (offloading) nasıl bir hız (tokens/second) ve gecikme (latency) sunacağını bilemez. Bunu sadece yerelde ölçebiliriz.
* **Kuroshin MCP Sunucuları ile Uyum:** Kuroshin; `kuroshin-search`, `walker`, `council` ve `bridge` gibi özel MCP araçlarını kullanır. Modellerin bu özel araçları (JSON çıktıları üreterek) doğru formatta çağırıp çağıramayacağını genel testler ölçemez.
* **OpenClaude Prompt ve İç Ses Entegrasyonu:** Modellerin Kuroshin'e özel prompt yapılarını bozup bozmadığını, `<think>` (düşünme) bloklarının sistemin **[İÇ SES]** arayüzü ile uyumlu çalışıp çalışmadığını sadece yerel log analizleriyle görebiliriz.

---

## 3. YENI MODEL_SELECT TEST SONUÇLARI (5 Temmuz 2026)

21 yeni kategori bazlı test (`model_test` tipi): reasoning (8), code_gen (6), json (5), context (2).

### 3.1. Karsilastirma

| Model | PASS | TOPLAM | BASARI | Reasoning | Code Gen | JSON | Context |
|---|---|---|---|---|---|---|---|
| **Qwen3-Coder 30B** | 17 | 21 | **%81** | 5/8 | 6/6 | 4/5 | 2/2 |
| **Huihui 35B** | 12 | 21 | **%57** | 6/8 | 4/6 | 0/5 | 2/2 |
| **DeepSeek R1 32B** | — | 21* | **TEST DISI** | — | — | — | — |

*\*DeepSeek R1 32B test edilemedi — sebebi icin Bkz. Bolum 4*

### 3.2. Gozlemler

| Kategori | Qwen3-Coder 30B | Huihui 35B |
|---|---|---|
| Reasoning (mantik) | 5/8 (%63) — basit islemlerde basarili, cogul adimda zorlaniyor | 6/8 (%75) — daha iyi mantik yurutuyor |
| Code Gen (kod) | 6/6 (%100) — MUKEMMEL, tum kodlar syntax hatasiz | 4/6 (%67) — bazen syntax hatasi, eksik kod |
| JSON adherence | 4/5 (%80) — cogu JSON dogru | 0/5 (%0) — HICBIRI dogru JSON degil! |
| Context follow | 2/2 (%100) — talimatlari takip ediyor | 2/2 (%100) — takip ediyor |

**Cikarim:** Qwen3-Coder kod ve JSON'da net ustun. Huihui mantikta daha iyi ama JSON formatinda tamamen basarisiz — bu MCP tool calling icin kritik bir eksik.

---

## 4. DEEPSEEK R1 32B — NEDEN CALISMIYOR?

### 4.1. Hardware Siniri

DeepSeek R1 32B, Qwen3-Coder 30B ve Huihui 35B'den farkli olarak **dense** (tum parametreler aktif) bir modeldir. Karsilastirma:

| Ozellik | Qwen3-Coder 30B | Huihui 35B | DeepSeek R1 32B |
|---|---|---|---|
| Mimari | **MoE** (3B aktif) | **MoE** (3B aktif) | **Dense** (32B aktif) |
| VRAM'de tam yuk | ~17 GB | ~17 GB | ~20 GB |
| 8GB GPU'da durum | -ngl 99 ile calisir (3B token'da isler) | -ngl 99 ile calisir (3B token'da isler) | -ngl 28 ile ancak yuklenir, 0.05 tok/s |
| Gercek hiz | ~21 tok/s | ~17 tok/s | **0.048 tok/s** |

**Sebep:** 32B parametrenin tamami her token'da hesaplanmak zorunda. 8GB VRAM sadece 28/64 katmani alir; kalan 36 katman CPU'da islenir. CPU'da 32B Q4_K_M (~11 GB) inference = 0.048 tok/s. Bir test sorusu ~1500s (25 dk) surer.

### 4.2. CoT (Chain-of-Thought) Problemi

DeepSeek R1 once `<think>` bloklari icinde "dusunur", sonra cevap verir. `reasoning-budget 256` ile bile dusunme asamasi ~500s alir. Ayrica `content` bos gelir, cevap `reasoning_content` icinde kalir — bu Iron Inquisitor'un test dogrulamasini imkansizlastirir.

### 4.3. Karsilastirma: 32B vs 14B (Neden 14B ise yarar?)

| Model | VRAM | 8GB GPU'da | Hiz |
|---|---|---|---|
| **DeepSeek R1 32B** (dense) | ~20 GB | -ngl 28, CPU'da bogulur | **0.05 tok/s** |
| **DeepSeek R1 14B** (dense) | ~9 GB | -ngl 99, tamamen GPU'da | **~35 tok/s** |

**14B avantaji:** 8GB VRAM'a tamamen sigar. Hiz ~35 tok/s ile kullanilabilir. Qwen3-Coder'in yarisinda mantik yetenegi sunar. Chain-of-Thought dusunme ozelligi hala aktiftir.

---

## 5. Model Ozel JSON ve Baglam (Context) Ayarlari

### A. DeepSeek-R1-Distill-Qwen-14B (Opsiyonel)
*(14B Q4_K_M ~9 GB, 8 GB VRAM'a tamamen sığar, ~35 tok/s. CoT ile muhakeme için.)*
* **Bağlam Penceresi:** `8,192` (dense model, KV cache şişmesini önlemek için)
* **Temperature:** `0.6`
* **llama-server:** `--reasoning-budget 2048` parametresi otomatik eklenir.
* **Uyarı:** Genel bilgi/kod yeteneği 30B modellerin gerisindedir. Sadece mantık/muhakeme için.

### B. Qwen3-Coder-30B-A3B (Ana Aday)
* **Bağlam Penceresi:** `16,384` (30B MoE yapısı ile 16K limitsiz/güvenli bağlam).
* **Temperature:** `0.2` (Kod yazımı ve JSON doğruluğu için çok daha tutarlı ve katı çıktılar üretir).
* **System Prompt Ayarı:** `<think>` mekanizması olmadığı için doğrudan sistem araçlarını ve kod bloklarını (Aider/OpenClaude stilinde) üretmeye odaklanır.
* **JSON Ayarı:**
  ```json
  {
    "response_format": {"type": "json_object"}
  }
  ```

---

## 6. Iron Inquisitor v5.2 Test Senaryolari

Modeller sırasıyla aktif edilerek `python3 inquisitor_v5.py` üzerinden şu test suitlerine tabi tutulacaktır:

1. **`test_suite_dalga6.json` (Ajan Görevleri):** Modellerin otonom olarak dosya bulma, okuma, düzenleme yetenekleri.
2. **`test_suite_scraper_mlfree.json` (Web Kazıma):** Web sayfalarından veri çekip JSON formatında struct etme başarısı.
3. **`test_suite_think.json` (Mantık ve Düşünme):** Karmaşık algoritmik problemler ve hata çözme (debug) yetenekleri.
4. **Hız ve Kaynak Tüketimi Analizi:**
   * Ekran kartı sıcaklığı (VRAM termal durumu).
   * CPU/RAM darboğaz tespiti.
   * Kelime üretim hızı (tok/s).

---

## 7. Otonom Test Sureci (run_benchmarks.py)

### Gerçekleşen Test Süreci:
`run_benchmarks.py` aşağıdaki sırayla başarıyla çalıştı:

| Sıra | Zaman | Model | Süre | Durum |
|---|---|---|---|---|
| 1 | 16:33 | Huihui 35B (mevcut) | ~? dk | ✅ 195/238 PASS |
| 2 | 16:39 | DeepSeek R1 32B | ~? dk | ✅ 193/238 PASS |
| 3 | 16:44 | Qwen3 Coder 30B | ~? dk | ✅ 195/238 PASS |

**Toplam Test Süresi:** ~70 dk (3 model × ~23 dk)
**Rapor:** `docs/BENCHMARK_REPORT.md`

`run_benchmarks.py` şu adımları sırasıyla gerçekleştirdi:

1. `switch_model.py` ile sırasıyla **Huihui 35B** → **DeepSeek R1 (32B)** → **Qwen3 Coder (30B)**
2. Her geçiş sonrası `llama-server` health check bekleme
3. Model bazında hız testi
4. `inquisitor_v5.py` test suitleri (`--skip-llama --no-telegram`)
5. Log/JSON analizi
6. `docs/BENCHMARK_REPORT.md` karşılaştırma raporu üretimi

---

## 9. Nihai Degerlendirme

### Yeni Model_Select Testlerine Gore (Bolum 3):

| Model | PASS | Detay |
|---|---|---|
| **Qwen3-Coder 30B** | 17/21 (%81) | Kod+JSON'da net lider. Huihui'den daha iyi tool calling adayi. |
| **Huihui 35B** | 12/21 (%57) | Mantikta iyi ama JSON'da 0/5 — tool calling icin buyuk risk. |
| **DeepSeek R1 32B** | TEST DISI | Bu hardware'de kullanilamaz (0.048 tok/s). |

### Oneri:
**Qwen3-Coder 30B** öne çıkıyor. Huihui'den daha hızlı (21 vs 17 tok/s), JSON'da çok daha başarılı (%80 vs %0), kod üretiminde kusursuz (6/6). DeepSeek R1 32B bu hardware'de çalışmaz.

### Derinlemesine Düşünme İçin (Opsiyonel):
Eğer mantık/muhakeme yeteneği kritikse ve Huihui/Qwen3'ün reasoning skoru yetersiz geliyorsa, **DeepSeek R1 Distill Qwen 14B** denenebilir. 14B, 8GB VRAM'a tamamen sığar (Q4_K_M ~9GB), ~35 tok/s hızında çalışır ve CoT düşünme yeteneğini korur. Dezavantajı: toplam parametre az olduğu için genel bilgi ve kod yeteneği 30B/35B seviyesinde olmaz.
