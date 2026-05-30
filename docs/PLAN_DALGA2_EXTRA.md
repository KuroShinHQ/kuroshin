# Dalga 2 EK Plan — Manuel Lord Operasyonları
**Oluşturma:** 29 Mayıs 2026
**Durum:** ⏸ Bekliyor — disk/ağ operasyonu gerektirir, Lord tarafından tetiklenir

Bu dosya, Dalga 2 Otomasyon paketinde **kod düzeyinde yapılamayan** (4-16GB indirme + servis kurulumu) iki E-paketinin adım adım talimatını içerir.

---

## E-09 · Llama Guard 3 Opsiyonel Post-Filter

### Amaç
Mevcut KILIÇ-KALKAN v4 (24 fonksiyon, pattern + Jaccard tabanlı) **çıktı üzerinde** ek güvenlik tarayıcısı kazandırmak. Llama Guard 3 (Meta) 8B chat-classifier modeli, üretim çıktısını "safe / unsafe + kategori" olarak etiketler.

### Risk-Maliyet
| | |
|--|--|
| **Disk** | ~5 GB (Q4_K_M GGUF) |
| **VRAM** | 4-5 GB (Huihui-35B aktif iken paralel çalışmaz — sırayla yüklenir veya CPU offload) |
| **Latency etkisi** | +200-400ms per response (CPU offload), +50-80ms (GPU paylaşımı) |
| **False positive** | ~5-8% (akademik kötülüğe meyilli — Türkçe içerikte daha yüksek olabilir) |
| **Faydası** | Edge-case'lerde defense in depth — KILIÇ-KALKAN'ın yakalayamadığı semantik agresif yanıtlar |

### Adımlar

**1. İndir (Lord PowerShell'den):**
```powershell
wsl -d Ubuntu-22.04 -e /bin/bash -c "cd /root/kuroshin/models && wget -c 'https://huggingface.co/bartowski/Llama-Guard-3-8B-GGUF/resolve/main/Llama-Guard-3-8B-Q4_K_M.gguf' -O llama_guard_3_8b_q4.gguf"
```

**2. Servis dosyası oluştur** (`scripts/start_llama_guard.sh`):
```bash
#!/bin/bash
BIN="/root/kuroshin/engines/llama.cpp/build/bin/llama-server"
MODEL="/root/kuroshin/models/llama_guard_3_8b_q4.gguf"
nohup $BIN -m "$MODEL" --host 127.0.0.1 --port 8082 \
    -ngl 0 -c 4096 --no-mmap --metrics \
    >> /mnt/c/Kuroshin/logs/llama_guard.log 2>&1 &
```

**3. Chancellor entegrasyon noktası** (`chancellor.py` `process_message` send_msg öncesi):
```python
# Llama Guard 3 post-output filter (opsiyonel — config flag ile aktif)
if os.getenv("LLAMA_GUARD_ENABLED", "false") == "true":
    guard_verdict = _llama_guard_classify(reply_text)
    if guard_verdict.get("unsafe"):
        _log(f"[LLAMA_GUARD] Çıktı unsafe: {guard_verdict.get('categories')}")
        reply_text = "⚔️ Lordum, ürettiğim yanıt güvenlik filtresinden geçemedi. Tekrar formüle ediyorum."
        # veya reply'i blokla, model'i tekrar çalıştır
```

**4. Iron Inquisitor test ekle** (`test_suite_security_v5.json`):
```json
{"id":"security-v5-llamaguard-01", "type":"security_check", "check":"llamaguard",
 "input":"<unsafe sample>", "expect_blocked":true, "weight":1.0}
```

**5. Bat menü ekle** (`Kuroshin.bat`):
```
[10] Llama Guard 3 başlat/durdur
```

### Karar Kriteri
**🟢 UYGULA** yalnızca:
- Lord public deployment düşünüyorsa (kuroshin'i internet'e açacaksa)
- Veya KILIÇ-KALKAN coverage'da production-tier compliance gerekirse (örn: enterprise müşteri)

**🔴 ATLA**:
- Sistem sadece Lord ile özel olarak konuşuyor → mevcut 24 fonksiyon yeterli
- 5GB disk dar gelirse

---

## E-16 · Qwen3-30B-A3B-Instruct-2507 Geçiş Denemesi

### Amaç
Mevcut Huihui-35B-A3B yerine **2507 nesil** modeli dene. Agent-tool-use için daha optimize, **262K natif context** (vs 16K mevcut), daha küçük (16.4GB vs 18.7GB).

### Risk-Maliyet
| | |
|--|--|
| **Disk** | ~16.4 GB (IQ4_XS GGUF) |
| **İndirme süresi** | 30-60 dk (HF mradermacher) |
| **VRAM/RAM** | Eşdeğer (her ikisi de A3B MoE, ~7.5 GB @ 64K KV q4_0) |
| **Beklenen hız** | 22-26 tok/s (Huihui: 20-21) — `-ot exps=CPU` korunur |
| **T1-T6 risk** | %99.03 eşdeğer olmayabilir — yeni karakter sızıntısı/format sorunu çıkabilir |
| **Geri dönüş** | Trivial: `switch_model.py switch huihui` |

### Adımlar

**1. İndir:**
```powershell
wsl -d Ubuntu-22.04 -e /bin/bash -c "cd /root/kuroshin/models && wget -c 'https://huggingface.co/mradermacher/Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated-i1-GGUF/resolve/main/Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated.i1-IQ4_XS.gguf'"
```

**2. switch_model.py kataloğa ekle** (`MODEL_HINTS`):
```python
{
    "match": "qwen3-30b-a3b-2507",
    "label": "Huihui-Qwen3-30B-A3B-Instruct-2507 IQ4_XS (MoE, 262K ctx)",
    "aliases": ["2507", "30b-2507", "qwen2507"],
    "context": 65536,  # 8GB VRAM'de 64K güvenli
    "moe": True,
},
```

**3. start_llama.sh MoE branch'inde** (zaten otomatik, ek ayar gerekmez):
```bash
# 30B-2507 için --reasoning-budget mevcut (3072) yeterli
# -ot "exps=CPU" zaten devrede
```

**4. Geçiş:**
```bash
python3 /mnt/c/Kuroshin/scripts/switch_model.py switch 2507
```

**5. E-17 ile A/B test (mevcut Dalga 2 paketinde hazır):**
```bash
python3 /mnt/c/Kuroshin/scripts/switch_model.py ab_test huihui 2507
```
Çıktı: `memory/ab_test_reports/ab_YYYYMMDD_HHMMSS.json`

**6. T1-T6 kalite testleri** (`scripts/quality_tests/`):
```bash
python3 /mnt/c/Kuroshin/scripts/quality_tests/t1_sohbet.py
# t2..t6 sırayla
```

**7. Iron Inquisitor full regresyon:**
```bash
python3 /mnt/c/Kuroshin/scripts/iron_inquisitor/inquisitor_v5.py --manifest master_manifest.json --tier core
```

### Karar Kriteri (T1-T6 + Inquisitor sonrası)
**🟢 KALICI GEÇİŞ:**
- T1-T6 ortalama ≥ 98.0 (Huihui'ye yakın)
- Iron Inquisitor 49/49 PASS (regression yok)
- Hız ≥ 20 tok/s

**🟡 KORU/PARALEL TUT:**
- Bazı testlerde düşük ama otonom döngüde 262K ctx avantajı net (örn. uzun zincir görevde)
- `switch_model.py` ile workload'a göre seç

**🔴 GERİ DÖN:**
- T1-T6 < 95 veya regression varsa: `switch_model.py switch huihui`

### Bağlam (Otonom ajan için kazanç)
30B-2507 ile **64K ctx** açılır. Bu, mevcut otonom döngüdeki bağlam kıtlığını çözer:

```
Mevcut (16K):
  L1 prompt ~1500 + tool schemas ~4200 + araç çıktısı ~10000
  = ~15700 / 16384 (sınıra dayanıyor)

2507 (64K):
  Aynı + reflexion buffer + plan-and-execute history
  = ~25000 / 65536 (geniş alan kalır)
```

E-05 (Reflexion buffer) ve E-06 (Plan-and-Execute) bu modelden tam fayda alır — 64K'da plan + history + retrieved docs yan yana sığar.

---

## Özet — Lord Karar Tablosu

| Paket | Disk | İş yükü | Ne zaman uygula? |
|-------|------|---------|------------------|
| **E-09 Llama Guard 3** | 5 GB | 1-2 saat | Public deployment veya compliance gerekirse |
| **E-16 Qwen3-30B-2507** | 16.4 GB | 1 saat indirme + E-17 A/B test (~10 dk) | İdeal: Reflexion + Plan-and-Execute ile birlikte denenir |

Önerim: **E-16 önce** (E-17 A/B test ile karşılaştır), karar belli olunca E-09 düşünülür.
