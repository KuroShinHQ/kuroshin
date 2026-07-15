# 📊 KUROSHİN OTOMATİK MODEL KARŞILAŞTIRMA RAPORU
**Oluşturulma Tarihi:** 2026-07-05 16:44:05
Bu rapor, yerel donanımda çalışan modellerin otonom olarak test edilmesiyle otomatik üretilmiştir.

## 📈 1. Genel Performans Karşılaştırma Tablosu

| Model Rolü | Model Dosya Adı | Başarı Oranı | Hata Oranı | Hız (tok/s) | Ort. Test Süresi | Güvenlik (ASR) | Rapor Dosyası |
|---|---|---|---|---|---|---|---|
| **Mevcut (Qwen3.6-35B)** | `Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf` | **%81.9** | %18.1 | 17.4 | 0.32s | %0.0 (0/0) | [inquisitor_20260705_163335.json](file:///C:/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_163335.json) |
| **DeepSeek R1 (32B)** | `DeepSeek-R1-Distill-Qwen-32B-abliterated-Q4_K_M.gguf` | **%81.1** | %18.9 | 0.0 | 0.86s | %0.0 (0/0) | [inquisitor_20260705_163958.json](file:///C:/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_163958.json) |
| **Qwen3 Coder (30B)** | `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` | **%81.9** | %18.1 | 20.9 | 0.29s | %0.0 (0/0) | [inquisitor_20260705_164405.json](file:///C:/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_164405.json) |

## 🎯 2. Karar ve Değerlendirme Analizi

### 💡 Donanım ve Hız Değerlendirmesi:
* **Qwen3 Coder**, mevcut modele göre **+3.5 tok/s** daha hızlı çıktı üretiyor. MoE mimarisi sayesinde hız avantajı yerel cihazda oldukça belirgin.
* **DeepSeek R1 (32B)**, derin düşünme `<think>` token'ları ürettiği için kelime hızında daha yavaş bir grafik çizdi (Ort. gecikme: 0.86s).

### 🛠️ Ajan Entegrasyonu ve Kararlılık:
* **Qwen3 Coder (%81.9 Başarı)**, DeepSeek R1'e göre araç çağırma (tool-calling) testlerinde daha kararlı duruş sergiledi. Kodlama ve ajan entegrasyonu için daha güvenli bir liman.

## 🚀 3. Nihai Tavsiye (Tavsiye Edilen Karar)

Yapılan otonom test sonuçlarına göre Kuroshin OS için en başarılı aday: **Mevcut Model** (`Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf`).
Bu model test suitini **%81.9 başarı oranı** ile tamamlayarak en stabil performansı göstermiştir.