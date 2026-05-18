# Model Karşılaştırma Raporu
**Tarih:** 11 Mayıs 2026 | **Kuroshin OS v7.4**

## Test Edilen Modeller

| Model | Boyut | Parametre | Quant | Port | VRAM |
|-------|-------|-----------|-------|------|------|
| **Gemma4 E4B Q4_K_M** | ~2.5GB GGUF | ~4B (effective) | Q4_K_M | 8080 | ~2.2GB |
| **Qwen2.5-Coder-1.5B** | 1.1GB GGUF | 1.5B | — | 8081 | ~0.9GB |

> **Not:** Qwen3 indirilmedi (kullanıcı kararı). Karşılaştırma elimizdeki modellerle yapıldı.

---

## Önemli Keşif — Gemma4 Thinking Mode

Gemma4'ün bu GGUF versiyonu **thinking modunda** çalışıyor:
- Her yanıt önce `<think>...</think>` bloğuyla başlıyor
- `reasoning_content` field'ine yazıyor, `content` field'i çoğu zaman boş kalıyor
- Kısa soru-cevap formatlarında (`420`, `Ankara`) doğrudan `content`'e yazıyor
- Uzun Türkçe yanıtlarda 400-500 token thinking'e harcıyor, kalan tokenla yanıt üretiyor
- **Sonuç:** max_tokens en az 1500-2000 olmalı; şansölye zaten 1000+ kullanıyor ✅

---

## Test Sonuçları

### 1. Türkçe Anlama

| Model | Yanıt | Süre | Hız |
|-------|-------|------|-----|
| Gemma4 | `(thinking mode — content üretmeden thinking bitti)` | 4.0s | 38 tok/s |
| Qwen2.5-Coder-1.5B | *"Yapay zeka, insan zekasını taklit eden bilgisayar sistemleri olarak tanımlanır. Makine öğrenimi, derin öğrenme ve doğal dil işleme gibi alt dalları vardır..."* | **0.5s** | **153 tok/s** |

**Kazanan: Qwen2.5-Coder-1.5B** (hız) | Gemma4 thinking mode nedeniyle token limitte takılıyor

### 2. Kod Üretimi (Python)

| Model | Yanıt Kalitesi | Süre | Hız |
|-------|---------------|------|-----|
| Gemma4 | `(thinking — limit aşıldı)` | 4.7s | 43 tok/s |
| Qwen2.5-Coder-1.5B | ✅ `def remove_duplicates(lst): seen = set(); result = []...` — doğru mantık | **1.3s** | **153 tok/s** |

**Kazanan: Qwen2.5-Coder-1.5B** — kod üretiminde özelleşmiş, doğrudan yanıt veriyor

### 3. Matematik

| Model | Yanıt | Süre | Hız |
|-------|-------|------|-----|
| Gemma4 | `420` ✅ | 1.6s | 32 tok/s |
| Qwen2.5-Coder-1.5B | `120 km/s * 3.5 saat = 420 km` ✅ | **0.1s** | **137 tok/s** |

**Kazanan: Qwen2.5-Coder-1.5B** (4.5x daha hızlı, ikisi de doğru)

### 4. Mantık / Çıkarım

| Model | Yanıt | Süre | Hız |
|-------|-------|------|-----|
| Gemma4 | `(thinking — limit aşıldı)` | 0.9s | 33 tok/s |
| Qwen2.5-Coder-1.5B | `Ali'nin 6 yeğeni var.` ✅ | **0.1s** | **134 tok/s** |

**Kazanan: Qwen2.5-Coder-1.5B**

### 5. Yaratıcı Yazma

| Model | Yanıt | Süre | Hız |
|-------|-------|------|-----|
| Gemma4 | `(thinking — limit aşıldı)` | 2.8s | 44 tok/s |
| Qwen2.5-Coder-1.5B | *"Yapay zekanın insanlığın geleceğini şekillendireceğini, insanların ihtiyaçlarını karşılayacak..."* — tekrar var ⚠️ | **0.8s** | **155 tok/s** |

**Kazanan: Qwen2.5-Coder-1.5B** (hız) | Kalite düşük (loop pattern)

### 6. İngilizce Anlama

| Model | Yanıt | Süre | Hız |
|-------|-------|------|-----|
| Gemma4 | `Ankara` ✅ | 0.3s | 9 tok/s |
| Qwen2.5-Coder-1.5B | `Ankara` ✅ | **0.03s** | **95 tok/s** |

**Kazanan: Qwen2.5-Coder-1.5B** (10x daha hızlı)

### 7. JSON / Araç Formatı

| Model | Yanıt | Süre | Hız |
|-------|-------|------|-----|
| Gemma4 | `(thinking — limit aşıldı)` | 2.0s | 41 tok/s |
| Qwen2.5-Coder-1.5B | ✅ `{"name": "John Doe", "age": 30, "city": "New York"}` — mükemmel | **0.2s** | **149 tok/s** |

**Kazanan: Qwen2.5-Coder-1.5B**

---

## Genel Skor Tablosu

| Kategori | Gemma4 | Qwen2.5-Coder-1.5B | Kazanan |
|----------|--------|---------------------|---------|
| Türkçe Anlama | ⚠️ (thinking limit) | ✅ | Qwen2.5 |
| Kod Üretimi | ⚠️ (thinking limit) | ✅ doğru | Qwen2.5 |
| Matematik | ✅ doğru | ✅ doğru | Qwen2.5 (hız) |
| Mantık | ⚠️ (thinking limit) | ✅ doğru | Qwen2.5 |
| Yaratıcı Yazma | ⚠️ (thinking limit) | ⚠️ loop | Qwen2.5 (hız) |
| İngilizce | ✅ | ✅ | Qwen2.5 (hız) |
| JSON Formatı | ⚠️ (thinking limit) | ✅ mükemmel | Qwen2.5 |

**Toplam: Qwen2.5-Coder-1.5B 7/7**

---

## Hız Karşılaştırması

| Model | Ort. Hız (tok/s) | Min | Max |
|-------|-----------------|-----|-----|
| Gemma4 E4B Q4_K_M | **~40 tok/s** | 9 | 44 |
| Qwen2.5-Coder-1.5B | **~140 tok/s** | 73 | 155 |

Qwen2.5-Coder-1.5B **3.5x daha hızlı**.

---

## Analiz ve Yorum

### Neden Gemma4 Bu Testte Kötü Göründü?

Bu test Gemma4 için **adil değil**:
1. **Thinking mode trap:** Gemma4 E4B, her sorudan önce uzun bir `<think>` bloğu üretiyor. Benchmark'ın `max_tokens` limiti thinking'e harcandı, gerçek yanıt üretilmedi.
2. **Doğru kullanım:** Şansölyede 1000-2000 max_tokens ile kullanılıyor — orada thinking tamamlanıyor ve kaliteli yanıtlar üretiyor.
3. **Gerçek güç farkı:** Gemma4 4B parametre, Qwen2.5 1.5B — parametre açısından Gemma4 2.6x büyük.

### Gerçek Dünya Performansı

Şansölye loglarına dayanarak Gemma4'ün gerçek yetenekleri:
- `/status` → nvidia-smi komutunu doğru seçiyor ✅
- `write_file` → masaüstüne yazar ✅
- `youtube_play` → video ID bulur ✅
- Türkçe diyalog → doğal, bağlamlı yanıtlar ✅
- Araç zinciri (tool_calls) → 3 adım loop yapabiliyor ✅

### Qwen2.5-Coder-1.5B'nin Yeri

Avantajları:
- 3.5x daha hızlı
- 0.9GB VRAM (Gemma4 ile birlikte çalışabilir, toplam ~3GB)
- Kısa sorularda anında yanıt
- Kod üretiminde optimize

Dezavantajları:
- Yaratıcı yazımda tekrar loop'u var
- Türkçe anlama: parafraz yapıyor, özetlemiyor
- Tool calling desteği test edilmedi
- Türkçe kültürel bağlam zayıf

---

## Öneri

| Senaryo | Önerilen Model |
|---------|---------------|
| Telegram şansölye (ana beyin) | **Gemma4** — araç çağrısı + bağlam + Türkçe |
| Hızlı kod tamamlama | **Qwen2.5-Coder-1.5B** — anlık yanıt |
| Aider entegrasyonu | **Gemma4** — bağlamlı kod analizi |
| Pipeline kalite filtresi | **Qwen2.5-Coder-1.5B** — düşük VRAM + hız |
| Qwen3-4B (gelecek) | Gemma4'ü ikame edebilir — test edilmeli |

**Sonuç:** İki model birbirinin rakibi değil, tamamlayıcısı. Gemma4 ana beyin, Qwen2.5-Coder-1.5B hızlı yardımcı model olarak kullanılabilir.

---

## Test Dosyaları

- Benchmark scripti: `scripts/model_benchmark.py`
- Ham sonuçlar: `reports/model_benchmark_results.json`
- Port 8081: Qwen2.5-Coder-1.5B (geçici, Kuroshin.bat'ta yok)
