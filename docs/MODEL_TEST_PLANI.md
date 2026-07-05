# 🧠 MODEL SWİTCHER TEST PLANI VE DEĞERLENDİRME REHBERİ

**Oluşturulma Tarihi:** 5 Temmuz 2026  
**Hedef Sistem:** Kuroshin OS (RTX 4060 Laptop 8GB VRAM + 32GB RAM)  
**Test Aracı:** Iron Inquisitor v5.2  

---

## 📌 1. Amaç ve Kapsam
Bu doküman, Kuroshin projesinin yerel yapay zeka beynini en doğru adaya taşımak için hazırlanmış resmi test planıdır. Sistemde aktif olan mevcut 35B modeli ile önerilen iki yeni 30B/32B seviyesindeki modeli yerel donanımımız ve otonom yazılım ajanımız (OpenClaude / Iron Inquisitor) üzerinde kıyaslayacağız.

### Karşılaştırılacak Modeller:
1. **Model A (Mevcut):** `Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf` (Konum: `/root/kuroshin/models/`, Boyut: 17.44 GB)
2. **Model B (Düşünme/Mantık Odaklı):** `DeepSeek-R1-Distill-Qwen-32B-abliterated-Q4_K_M.gguf` (Konum: `C:\Kuroshin\models\`, Boyut: 19.85 GB - *İndirme durumu: İNDİRİLDİ ✅*)
3. **Model C (Ajan/Hız Odaklı):** `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` (Konum: `C:\Kuroshin\models\`, Boyut: 18.54 GB - *İndirme durumu: İNDİRİLDİ ✅*)

---

## 📌 2. Soru-Cevap: Hugging Face Benchmarks vs. Yerel Testler
> **Soru:** *HF gibi sitelerde bu modellerin test sonuçları zaten var mı? Yerelde tekrar test etmeye gerek var mı?*

**Cevap:** Hugging Face üzerindeki testler genel akademik veri setlerine (HumanEval, MBPP vb.) ve sınırsız bulut kaynaklarına dayanır. **Yerel olarak test etmemiz kesinlikle zorunludur çünkü:**

* **Donanım Paylaşımı ve Hız Testi (RTX 4060 + 32GB RAM):** Hugging Face, modellerin ekran kartınızın VRAM'i ile sistem RAM'iniz arasında bölünerek (offloading) nasıl bir hız (tokens/second) ve gecikme (latency) sunacağını bilemez. Bunu sadece yerelde ölçebiliriz.
* **Kuroshin MCP Sunucuları ile Uyum:** Kuroshin; `kuroshin-search`, `walker`, `council` ve `bridge` gibi özel MCP araçlarını kullanır. Modellerin bu özel araçları (JSON çıktıları üreterek) doğru formatta çağırıp çağıramayacağını genel testler ölçemez.
* **OpenClaude Prompt ve İç Ses Entegrasyonu:** Modellerin Kuroshin'e özel prompt yapılarını bozup bozmadığını, `<think>` (düşünme) bloklarının sistemin **[İÇ SES]** arayüzü ile uyumlu çalışıp çalışmadığını sadece yerel log analizleriyle görebiliriz.

---

## 📌 3. Model Özel JSON ve Bağlam (Context) Ayarları

Her modelin kendine has çalışma yapısına göre `switch_model.py` ve `config/` dizini altında yapılandırılacak profiller ve yapılan optimum otomatik ayarlar:

### A. DeepSeek-R1-Distill-Qwen-32B (Düşünme Profili)
* **Bağlam Penceresi (Context Window):** 8GB VRAM RTX 4060 GPU performansı gözetilerek `16,384` olarak ayarlandı (varsayılan 64K context, KV Cache şişmesi ve aşırı CPU yavaşlamasına neden oluyordu). `switch_model.py` üzerinde 32B modeller için 16K limiti otomatik tanımlandı.
* **Temperature:** `0.6` (Düşünme modellerinde yaratıcılık ve self-correction için idealdir).
* **System Prompt Ayarı:** Modelin `<think>` etiketlerini kaybetmemesi sağlanmalıdır. Çıktılar doğrudan `[İÇ SES]` etiketine yönlendirilir.
* **llama-server Entegrasyonu:** `start_llama.sh` betiği güncellenerek model isminde `deepseek` veya `r1` geçtiğinde, JSON formatıyla uyumlu çalışabilmesi için `--reasoning-budget 2048` parametresi otomatik olarak komuta eklenir.

### B. Qwen3-Coder-30B-A3B (Hızlı Kodlama/Ajan Profili)
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

## 📌 4. Iron Inquisitor v5.2 Test Senaryoları

Modeller sırasıyla aktif edilerek `python3 inquisitor_v5.py` üzerinden şu test suitlerine tabi tutulacaktır:

1. **`test_suite_dalga6.json` (Ajan Görevleri):** Modellerin otonom olarak dosya bulma, okuma, düzenleme yetenekleri.
2. **`test_suite_scraper_mlfree.json` (Web Kazıma):** Web sayfalarından veri çekip JSON formatında struct etme başarısı.
3. **`test_suite_think.json` (Mantık ve Düşünme):** Karmaşık algoritmik problemler ve hata çözme (debug) yetenekleri.
4. **Hız ve Kaynak Tüketimi Analizi:**
   * Ekran kartı sıcaklığı (VRAM termal durumu).
   * CPU/RAM darboğaz tespiti.
   * Kelime üretim hızı (tok/s).

---

## 📌 5. Otonom Test Süreci (run_benchmarks.py)
Modellerimiz yerel olarak indiği için test sürecini tamamen otonomlaştıran `run_benchmarks.py` betiğini kullanacağız. Bu betik sırasıyla şu adımları kendisi yapar:

1. `switch_model.py` üzerinden sırasıyla **Mevcut (Huihui 35B)**, **DeepSeek R1 (32B)** ve **Qwen3 Coder (30B)** modellerini aktif eder.
2. Her model geçişinden sonra `llama-server`'ın ayağa kalkmasını ve sağlıklı (`health check`) olmasını bekler.
3. Model bazında hız testi gerçekleştirir.
4. `inquisitor_v5.py` test suitlerini `--skip-llama --no-telegram` parametreleriyle otomatik olarak koşturur.
5. Her testin loglarını ve JSON çıktılarını analiz eder.
6. Son adımda tüm sonuçları kıyaslayan **`docs/BENCHMARK_REPORT.md`** karşılaştırma raporunu üretir.

### Testleri Çalıştırma Komutu:
WSL / Ubuntu terminalinde şu komutu çalıştırmamız yeterlidir:
```bash
source /root/kuroshin/venv/bin/activate
python3 /mnt/c/Kuroshin/scripts/iron_inquisitor/run_benchmarks.py
```

## 📌 6. Başarı Kriterleri ve Seçim Kararı
Testler bittikten sonra üretilen karşılaştırma raporu üzerinden şu kriterlere göre nihai seçim kararı verilecektir:

* **Araç Çağırma (Tool Calling) Başarısı:** %95 üzeri olmalı (otonom ajan işlevleri için kritik).
* **Ortalama Test Süresi ve Hız (Tolerans Sınırı):** Ekran kartımızda (RTX 4060) paylaşımlı çalışırken kelime üretim hızının **5 tok/s** değerinin altına düşmemesi istenir.
* **Güvenlik (ASR - Attack Success Rate) Skoru:** Modellerin jailbreak ve güvenlik testlerini engelleme oranı.
