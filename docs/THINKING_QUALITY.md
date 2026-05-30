# Kuroshin OS — Thinking Quality & Cognitive Steering (v3.0)
**Tarih:** 23 Mayıs 2026
**Vizyon:** Modelin `<think>` bloğunu karanlık kutu olmaktan çıkarıp yönlendirilebilir (steerable) ve ölçülebilir (measurable) bir Bilişsel Motor haline getirmek.

---

## 1. Mevcut Durum → Hedef

| Özellik | Mevcut (Low Effort) | Hedef |
| :--- | :--- | :--- |
| **Think Görünürlüğü** | `<think>` atılıyor, loglanmıyor | JSONL formatında her adım kaydedilir |
| **Düşünce Yapısı** | Serbest metin, yönsüz | 4 Zorunlu Adım: INTENT → STRATEGY → SECURITY → REFINEMENT |
| **Interleaved Thinking** | Sadece ilk turda düşünme | Araç sonuçlarından sonra tekrar düşünme |
| **Kalite Kontrolü** | Yok | ThinkPRM analog: her adım skorlanır |
| **Semantic Grounding** | Yok | Dosya/port durumu `<think>` bloğuna enjekte edilir |
| **Fault Detection** | Kısmi (monitor_think_drift) | Genişletilmiş döngü/sapma dedektörü |
| **Audit Trails** | Yok | SHA256 imzalı değiştirilemez karar logları |
| **Kritik Komut Çift Kontrol** | Yok | Aynı model 2× doğrulama (self-consistency analog) |

---

## 2. Bilişsel Yönlendirme Protokolü — 4 Zorunlu Adım

`system_prompt` katmanına eklenecek direktif:

```
<think> bloğunda sırasıyla şu adımları yaz:
[INTENT]    Lord'un asıl amacı ne? Gizli ihtiyaç var mı?
[STRATEGY]  Hangi araç en verimli? Neden?
[SECURITY]  Bu eylem KILIC-KALKAN kurallarını ihlal eder mi?
[REFINEMENT] Yanıt "Gold Signal" mi? Gürültüsüz mü?
```

---

## 3. Teknik Uygulama Planı (AJAN-12)

### TK-01: Think Chain Logger
`chancellor.py` → `_strip_think()` içine, ham düşünce silinmeden önce kayıt:
```
logs/think_chain/YYYY-MM-DD.jsonl
{"ts":..., "user_msg":..., "think_raw":..., "tool_called":..., "score":...}
```

### TK-02: Interleaved Reasoning (Araçlar Arası Düşünme)
Araç sonucu geldikten sonra model düşünmeden yanıta geçiyor.
**Yeni akış:** Araç Sonucu → `<think>` (Yeterli mi? Tekrar araç lazım mı?) → Final Yanıt.

### TK-03: Think Quality Scorer
`_score_think(think_text)` fonksiyonu:
- 4 etiket (INTENT/STRATEGY/SECURITY/REFINEMENT) var mı? → +40p
- Türkçe oran ≥%80? → +20p
- Uzunluk ≥300 karakter? → +20p
- Seçilen araç ile sonuç eşleşiyor mu? → +20p

### TK-04: Symbolic Grounding (Bağlam Enjeksiyonu)
`_think_turn()` içine sistem durumu enjeksiyonu:
- Açık portlar (8080/9002/9004)
- ChromaDB kayıt sayısı
- Aktif görev ID'si
→ `<think>` bloğuna "Sembolik Çapa" olarak ekle

### TK-05: Verifiable Audit Trails
`logs/audits/` dizini — TK-01 logger çıktısına SHA256 imzası ekle (BLUE-MEM-02 altyapısı).
Her karar kaydı: silinemeyen, hash zincirleme referansıyla.

### TK-06: Reasoning Fault Detector (Genişletilmiş)
`monitor_think_drift()` zaten var → genişlet:
- Döngü tespiti (aynı araç 3×+ tekrar)
- Semantik sapma (INTENT'ten uzaklaşma)
- Boş/kısa think (< 50 karakter) uyarısı

### TK-07: Kritik Komut Çift Kontrol (Self-Consistency Analog)
`rm -rf`, `git push --force`, `write_file` kritik parametreler için:
aynı model 2× farklı sıcaklıkta (temp=0.3 / temp=0.7) sorgula → tutarsızsa Telegram uyarı.

### TK-08: Sandbox Dry-Run Modu
Tüm kritik araçlara `dry_run=True` parametresi ekle → gerçek işlem yapmadan sonucu simüle et.
`formal_safety_check()` altyapısı kullanılır.

### TK-09: Iron Inquisitor — `think_quality` Test Suite
`test_suite_think.json` oluştur:
- think_log_01: Logger dosyaya yazıyor mu?
- think_steps_01: 4 adım etiket var mı?
- think_score_01: Skor ≥70 mu?
- think_interleaved_01: Araç sonrası think tetikleniyor mu?

---

## 4. Uygulama Sırası

| # | Görev | Durum | Süre |
|---|-------|-------|------|
| TK-01 | Think Logger | ✅ TAMAM | — |
| TK-02 | Think Steering (4 adım + Türkçe) | ✅ TAMAM | — |
| TK-03 | Think Scorer | ✅ TAMAM | — |
| TK-04 | Symbolic Grounding | ✅ TAMAM | — |
| TK-05 | Audit Trails (SHA256 imza) | ✅ TAMAM | — |
| TK-06 | Fault Detector (genişletilmiş) | ✅ TAMAM | — |
| TK-07 | Çift Kontrol | ✅ TAMAM | — |
| TK-08 | Dry-Run | ✅ TAMAM | — |
| TK-09 | Inquisitor Suite (8/8 %100) | ✅ TAMAM | — |

---

## 5. İlgili Araştırma

- [Claude Extended Thinking — Interleaved](https://docs.claude.com/en/docs/build-with-claude/extended-thinking)
- [ThinkPRM — Process Reward Models That Think (arXiv 2504.16828)](https://arxiv.org/abs/2504.16828)
- [Feature Extraction and Steering for CoT (arXiv 2505.15634)](https://arxiv.org/pdf/2505.15634)
- [Qwen3 reasoning-budget llama.cpp](https://github.com/ggml-org/llama.cpp/issues/20182)
