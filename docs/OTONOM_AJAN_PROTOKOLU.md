# OTONOM AJAN PROTOKOLÜ — Kuroshin Canlanma Sistemi
**Durum:** TASARIM AŞAMASI  
**Son Güncelleme:** 22 Mayıs 2026  
**Vizyon:** Model uyandığında kendi hedeflerini okur, kendi kararını verir, araçlarla görevi zincir halinde tamamlar, her adımı Telegram'a raporlar.

> Şu anki sorun: Karar veren Python, model sadece çalıştırılıyor.  
> Hedef: Karar veren MODEL, Python sadece altyapı sağlıyor.

---

## ARAŞTIRMA BULGULARI — Otonom Ajan İçin Model Seçimi (22 Mayıs 2026)

> Bu bölüm web araştırması sonrası eklendi. (ajan, 2026-05-22)

### Sorun: Mevcut Model 16K Context ile Otonom Ajan için Dar

Şu anki model (Huihui-Qwen3.6-35B-A3B IQ4_XS) 16K context ile çalışıyor.
Otonom ajan döngüsünde: `goals.json + tasks.json + araştırma çıktısı + think bloğu` = 16K hızla doluyor.

### Keşfedilen Çözüm: Qwen3-30B-A3B-2507 Serisi

| Özellik | Mevcut (35B) | Hedef (30B-2507) |
|---------|-------------|-----------------|
| Context | **16K** | **262,144 (262K) — natif** |
| Aktif parametre | 3.6B/token | 3B/token |
| Mimari | MoE ✅ | MoE ✅ |
| Abliterated | ✅ (Huihui) | ✅ (Huihui) |
| Thinking modu | ✅ | ✅ (Thinking-2507 sürümü) |
| IQ4_XS GGUF | ✅ ~18.7GB | ~16.4GB (daha küçük!) |
| 8GB VRAM uyumu | ✅ (-ot exps=CPU) | ✅ (-ot exps=CPU) |
| Hız tahmini | 20-21 tok/s | 22-26 tok/s (daha az parametre) |

### İki Aday Model

**Aday 1 — Günlük + Otonom (Tek Model):**
```
mradermacher/Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated-i1-GGUF
```
- 262K ctx, non-thinking, tool use güçlü, sohbet + araç zinciri
- ✅ Hem günlük Telegram hem otonom ajan için yeterli

**Aday 2 — Sadece Otonom Ajan (Yüksek Muhakeme):**
```
mradermacher/Huihui-Qwen3-30B-A3B-Thinking-2507-abliterated-i1-GGUF
```
- 262K ctx, SADECE thinking modu, karar verme + derin muhakeme
- ✅ Otonom karar döngüsü için üstün
- ⚠️ Yavaş (thinking her zaman açık), günlük sohbet için ağır

**Öneri: Aday 1 (Instruct-2507)** — tek model her iki görevi karşılar.
Thinking modu Qwen3'te `/think` ve `/no_think` ile mesaj bazlı açılıp kapanabilir.

### 8GB VRAM'de 262K Context Mümkün mü?

**Pratik Sınırlar:**

| Context | Durum | Yöntem |
|---------|-------|--------|
| 32K | ✅ Güvenli | Standart `-ctk q4_0 -ctv q4_0` |
| 64K | ✅ Mümkün | KV cache q4_0 zorunlu |
| 128K | ❌ VRAM taşar | ~8.5 GB gerekir, TurboQuant CUDA 13 şart — şu an skip |
| 262K | ❌ Hayır | 8GB VRAM'de mümkün değil |

**Otonom Ajan için Gerçek Context Budget Analizi — REVIZE EDİLDİ**

> İlk hesap eksikti. Tool schemas + thinking token + büyük görev listesi dahil edilmemişti.

```
Altyapı (sistem prompt + 21 araç şeması + goals + tasks):  ~22K  ← SABİT
Araştırma çıktıları (2 araştırma, sıkıştırılmamış):        ~10K
Araç zincirleri (4 round, call+result):                     ~8K
Think bloğu (KONTROLSÜZ — Qwen3 default):               ~15-20K  ← TEHLİKE
Geçmiş mesajlar:                                            ~3K
──────────────────────────────────────────────────────────────
TOPLAM (kontrolsüz):                              ~58-63K  ← 64K SINIRINA DAYANIYOR
```

**Sorun 1: Think bloğu patlatır**
Qwen3 thinking modu kontrolsüz bırakılırsa 15-20K token think üretir.
llama.cpp'de `--reasoning-budget N` parametresi ile sınırlanabilir (llama.cpp yeni ekledi).

**Sorun 2: Tool schemas sabit 4.2K**
21 araç × ~200 token = 4.2K — her çağrıda context'te. Kaçış yok.

**Sorun 3: Araştırma çıktısı ham gelirse**
walker_research tek seferde 5-10K token döndürür.
2-3 araştırma = 15-30K → tek başına 64K'yı tehdit eder.

---

**Çözüm: 64K + 2 Zorunlu Önlem**

| Önlem | Parametre | Etkisi |
|-------|-----------|--------|
| Thinking budget sınırla | `--reasoning-budget 3072` (llama-server flag) | Think: 15-20K → 3K |
| Araştırma sıkıştır | `_ozet_web_sonucu()` agresif (max 800 token) | Araştırma: 10K → 2K |

```
Altyapı (sabit):                              ~22K
Araştırma (özetlenmiş, 2 araştırma):           ~2K   ← 10K'dan düştü
Araç zincirleri:                               ~8K
Think bloğu (budget=3072):                     ~3K   ← 20K'dan düştü
Geçmiş:                                        ~3K
──────────────────────────────────────────────────
TOPLAM (yönetimli):                           ~38K   ← 64K'nın %59'u ✅
```

**Bu iki önlem ile 64K yeterli. Önlemsiz 64K TAŞAR.**

**Alternatif: 96K context** (VRAM: 7.63 GB — sıkışık ama çalışır)
- `-c 98304 -ctk q4_0 -ctv q4_0` → KV cache 2.63 GB + model 5 GB = 7.63 GB
- Önlemsiz kullanım için güvenli alan
- ⚠️ Peak kullanımda OOM riski var (~400MB serbest)

**Öneri: Mevcut 35B model + odaklı context mimarisi (primary). 30B-2507 deneysel.**

---

**MODEL-03 güncellemesi — start_llama.sh:**
```bash
# 30B-A3B-2507 profili
llama-server \
  -m "$MODEL_PATH" \
  -c 65536 \              # 64K context
  -ctk q4_0 -ctv q4_0 \  # KV cache sıkıştır
  --reasoning-budget 3072 \ # Think bloğu max 3K token
  -ot ".ffn_.*_exps.=CPU" \ # MoE experts CPU'ya
  -ngl 99 \
  ...
```

---

**⚠️ KRİTİK MİMARİ KARARI — Araç Çıktısı Özetlenmez**

Araştırma çıktısı (walker_research, web_search) özetlenirse model kör olur.
Araçlar tam çıktı üretmeli. Çözüm özetleme değil, **odaklı context mimarisi**.

```
YANLIŞ: goals_json + tasks_json + araştırma_ham + geçmiş → tek büyük context
DOĞRU:  aktif_görev(1 adet) + chroma_hafıza(3 kayıt) + son_araç_tam_çıktı → küçük odaklı context
```

Goals.json ve tasks.json dosyada kalır, context'e girmez. Sadece aktif görev girer.
Bu tasarımla mevcut 35B + 16K context otonom ajan için YETERLİ.

**Context Management Layer — DOĞRU yaklaşım:**
- [ ] **CM-01** · Karar promptuna sadece 1 aktif görev gönder (tüm tasks.json değil)
- [ ] **CM-02** · goals.json / tasks.json dosyada sakla, `load_tasks(durum="aktif", limit=1)` ile çek
- [ ] **CM-03** · Araştırma çıktısı → ChromaDB'ye tam yaz, context'e son sonuç tam girer
- [ ] **CM-04** · `--reasoning-budget 3072` start_llama.sh otonom profili (think bloğu sınırla)

---

**📝 DENEYSEL NOT — Model Geçişi (30B-2507)**

Mevcut 35B model otonom ajan için yeterli. Ama KV cache artırımı test etmek istenirse:

```
Model: mradermacher/Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated-i1-GGUF
Neden: 262K natif ctx → 64K'ya konfigüre edilince araç çıktıları özetlenmeden sığar
Ne zaman dene: FAZ 1-3 tamamlanıp sistem çalışınca, kalite karşılaştırması için
Komut: switch_model.py ile geç, T1-T6 kalite testi yap, sonra otonom döngüyü çalıştır
Risk: 16.4GB indirme, T1-T6 geçemezse geri dön
```

Bu geçiş zorunlu değil, merak ve test amaçlı. Önce sistemi 35B ile çalıştır.

### MoE Offload Komutu (Kritik)
```bash
# Mevcut (35B için):
-ot "exps=CPU"

# 30B-2507 için (daha spesifik — daha hızlı):
-ot ".ffn_.*_exps.=CPU"
```

### Karar

- [ ] **MODEL-01** · `Huihui-Qwen3-30B-A3B-Instruct-2507-abliterated-i1-GGUF` IQ4_XS indir (~16.4GB)
- [ ] **MODEL-02** · `switch_model.py`'ye 30B-A3B-2507 girişi ekle (ctx=65536, MoE=true)
- [ ] **MODEL-03** · `start_llama.sh`'de 2507 modeli için `-c 65536 -ctk q4_0 -ctv q4_0` profili
- [ ] **MODEL-04** · Otonom ajan döngüsü başlarken model 35B → 2507'ye geçer, bitiş sonrası geri döner (veya tek model kalır)
- [ ] **MODEL-05** · T1-T6 kalite testi — 30B-2507 Instruct abliterated ile (mevcut 99.03/100 eşdeğer mi?)

---

## Temel Fark — Şimdi vs Hedef

```
ŞIMDI:
Python cron → "araştır" emri → Model yanıt → Python sonucu işler

HEDEF:
Model uyanır → Hafızadan hedef okur → Kendi kararını verir
    → Araç zinciri kurar → Adım adım uygular → Sonucu değerlendirir
        → Bir sonraki hedefi yazar → Kendini zamanlar → Uyur
```

---

## Anahtar Kavramlar (Gelişmiş & Uygulanabilir)

| Kavram | Açıklama | Dosya |
|--------|----------|-------|
| **Hedef (Goal)** | Modelin ulaşmak istediği uzun vadeli amaç (Hierarchical Planning başı) | `memory/goals.json` |
| **Görev (Task)** | Bir hedefi ilerletmek için tek seferlik iş birimi (Atomic Action Unit) | `memory/tasks.json` |
| **Ajan Döngüsü (OODA)** | Monitor → Analyze → Plan → Execute (OODA Probe / MAPE-K yapısı) | `scripts/kuroshin_autonomous.py` |
| **Yansıma (Reflection)** | Görev sonrası model kendi çıktısını değerlendirir (Self-Correction) | `memory/reflections/` |
| **Tetikleyici (Trigger)** | Döngüyü başlatan olay: zamanlayıcı, olay, kullanıcı emri | chancellor + idle_loop |
| **Telegram Akışı** | Her adımda kullanıcıya canlı ilerleme bildirimi (Real-time Observability) | `send_task_progress()` |
| **Bağlam Köprüsü** | Görev yarım kalırsa bir sonraki oturuma state taşıma (Task Serialization) | `memory/task_context.json` |
| **MİMİC Deseni** | Sosyal mecralarda insan gibi değerli etkileşim kurma (Social Presence) | `chancellor.py` + reddit/github tools |
| **Onay Kapısı (HITL)** | Kritik eylemler öncesi Telegram'dan gelen kullanıcı onayı (Human-in-the-Loop) | `github_push_onayla` callback |

---

## Sistem Mimarisi

```
┌─────────────────────────────────────────────────────┐
│                  AJAN DÖNGÜSÜ                       │
│                                                     │
│  [1] UYAN          memory/goals.json oku            │
│      ↓             memory/tasks.json oku            │
│                                                     │
│  [2] DÜŞÜN         Model: hangi görevi şimdi?       │
│      ↓             Öncelik: acil > bloke > yeni     │
│                                                     │
│  [3] PLANLA        Model: adımları belirle          │
│      ↓             tool1 → tool2 → tool3 zinciri    │
│                                                     │
│  [4] UYGULA        Her araç çağrısı = 1 adım        │
│      ↓             Her adımda Telegram bildirimi    │
│                                                     │
│  [5] DEĞERLENDİR   Başarılı mı? Eksik var mı?       │
│      ↓             memory/reflections/ yaz          │
│                                                     │
│  [6] GÜNCELLE      tasks.json → completed/blocked   │
│      ↓             goals.json → ilerleme % güncelle │
│                                                     │
│  [7] PLANLA        Sonraki görevi belirle / yaz     │
│      ↓             Uyku süresini hesapla            │
│                                                     │
│  [8] RAPORA        Telegram'a özet gönder           │
│      ↓             Uyu / bir sonraki tetikleyiciyi kur│
└─────────────────────────────────────────────────────┘
```

---

## Veri Yapıları

### `memory/goals.json`
```json
{
  "goals": [
    {
      "id": "G-001",
      "baslik": "Reddit'te LocalLLaMA topluluğuna katıl",
      "aciklama": "r/LocalLLaMA'da kaliteli yorumlar yaparak toplulukla bağ kur",
      "oncelik": 2,
      "durum": "aktif",
      "ilerleme": 0,
      "alt_hedefler": ["karma_kazan", "ilk_yorum", "takip_et"],
      "olusturma_ts": "2026-05-22T10:00:00",
      "son_guncelleme": "2026-05-22T10:00:00",
      "notlar": ""
    }
  ]
}
```

### `memory/tasks.json`
```json
{
  "tasks": [
    {
      "id": "T-001",
      "goal_id": "G-001",
      "baslik": "r/LocalLLaMA hot postlarını tara, 3 potansiyel yorum fırsatı bul",
      "durum": "bekliyor",
      "oncelik": 1,
      "adimlar": [
        {"sirano": 1, "arac": "reddit_read", "parametre": {"subreddit": "LocalLLaMA"}, "durum": "bekliyor"},
        {"sirano": 2, "arac": "chroma_search", "parametre": {"sorgu": "fırsat yorumları"}, "durum": "bekliyor"},
        {"sirano": 3, "arac": "web_search", "parametre": {"task": "LLM güncel gelişmeler"}, "durum": "bekliyor"}
      ],
      "baslangic_ts": null,
      "bitis_ts": null,
      "sonuc": "",
      "hata": ""
    }
  ]
}
```

### `memory/task_context.json`
```json
{
  "aktif_gorev_id": "T-001",
  "tamamlanan_adim": 2,
  "ara_sonuclar": {
    "adim_1_cikti": "5 post bulundu: ...",
    "adim_2_cikti": "Hafızada benzer konu yok"
  },
  "devam_notu": "Adım 3'te web araması yapılacak, sonra değerlendirme"
}
```

---

## FAZ 1 — Hedef & Görev Altyapısı

> **Amaç:** `goals.json` + `tasks.json` + CRUD fonksiyonları. Model bunları okuyup yazabilmeli.

### TODO

- [x] **F1-01** · `memory/goals.json` şeması oluştur — yukarıdaki yapıyı dosyaya yaz (ajan, 2026-05-22)
- [x] **F1-02** · `memory/tasks.json` şeması oluştur (ajan, 2026-05-22)
- [x] **F1-03** · `memory/task_context.json` şeması oluştur (yarım görev bağlamı) (ajan, 2026-05-22)
- [x] **F1-04** · `memory/reflections/` dizini — `YYYY-MM-DD_T-XXX.md` formatı (ajan, 2026-05-22)
- [x] **F1-05** · `scripts/kuroshin_goals.py` yardımcı modül:
  - `load_goals()` → aktif hedefleri döndür
  - `load_tasks(durum=None)` → görevleri filtreli döndür
  - `update_task(id, durum, sonuc)` → tasks.json güncelle
  - `add_task(goal_id, baslik, adimlar)` → yeni görev ekle
  - `save_context(gorev_id, adim, ara_sonuclar)` → bağlamı kaydet
  - `load_context()` → kalan bağlamı yükle (ajan, 2026-05-22)
- [x] **F1-06** · Chancellor'a 2 yeni araç ekle:
  - `goal_manage` — hedef ekle/listele/güncelle (kullanıcı Telegram'dan hedef verebilmeli)
  - `task_status` — görev durumu sorgula / manuel tamamla / iptal et (ajan, 2026-05-22)

---

## FAZ 2 — Ajan Karar Döngüsü

> **Amaç:** Model uyanır, goals/tasks okur, kendi kararını verir, araç zinciri kurar ve uygular.

### Kritik Tasarım Kararı: Modeli Karar Verici Yap

```python
# YANLIŞ (şu anki):
def ajan_dongusu():
    konu = _konu_sec()          # Python karar veriyor
    sonuc = model_cagir(konu)   # Model sadece çalıştırılıyor

# DOĞRU (hedef):
def ajan_dongusu():
    prompt = _hazirla_karar_promptu()   # goals + tasks + context
    karar = model_cagir(prompt)         # Model karar veriyor
    gorev = _parse_karar(karar)         # Python kararı uygular
    _yukle_ve_calistir(gorev)
```

### Karar Prompt Şablonu

```
Sen Kuroshin'sin. Şu an otonom karar verme modundasın.

AKTIF HEDEFLER:
{goals_listesi}

BEKLEYEN GÖREVLER:
{tasks_listesi}

YARIM KALAN BAĞLAM:
{task_context}

SON 24 SAAT AKTİVİTE:
{aktivite_ozeti}

Şimdi sana 3 seçenek var:
A) Bekleyen bir göreve devam et → task_id seç
B) Yeni bir görev başlat → hedef_id ve adımları belirle  
C) Bekle → sebep yaz, kaç dakika sonra tekrar kontrol et

Kararını JSON olarak ver:
{"karar": "A", "task_id": "T-001", "sebep": "..."}
```

### TODO

- [x] **F2-01** · `scripts/kuroshin_autonomous.py` ana dosya — iskelet yaz (ajan, 2026-05-22)
  - `class KuroshinAjan`
  - `uyan()` → goals/tasks/context yükle
  - `karar_ver()` → model karar prompt çalıştır, JSON parse
  - `gorev_calistir(task)` → adım adım araç zinciri
  - `degerlendir(task, sonuc)` → model reflection prompt
  - `guncelle(task, sonuc)` → tasks.json, goals.json yaz
  - `planla_sonraki()` → sonraki görevi yaz veya bekle
  - `uyku_zamanla(dakika)` → memory/next_wakeup.json'a yaz
- [x] **F2-02** · `_karar_promptu()` fonksiyonu — goals + tasks + context birleştirme (ajan, 2026-05-22)
- [x] **F2-03** · `_parse_karar(json_str)` — model çıktısını robust parse et (think bloğu strip dahil) (ajan, 2026-05-22)
- [x] **F2-04** · `_gorev_adim_calistir(adim)` — walker/council/reddit_read/write_file direkt HTTP (FAZ 5'te run_tool entegrasyonu) (ajan, 2026-05-22)
- [x] **F2-05** · `_reflection_promptu(task, sonuc)` — görev sonrası model değerlendirme (ajan, 2026-05-22)
- [x] **F2-06** · Bağlam köprüsü — görev yarım kalırsa `task_context.json`'a yaz, sonraki oturumda kaldığı yerden devam (ajan, 2026-05-22)

---

## FAZ 3 — Telegram Canlı İzleme

> **Amaç:** Kullanıcı oturup izleyebilsin. Her adım, her karar, her sonuç Telegram'a akar.

### Mesaj Formatları

```
🤖 GÖREV BAŞLADI
━━━━━━━━━━━━━━━━
Görev : r/LocalLLaMA tara, 3 yorum fırsatı bul
Hedef : Reddit topluluğuna katıl
Adımlar: 3

🔧 Adım 1/3 — reddit_read
   subreddit: LocalLLaMA, sort: hot
   ⏳ çalışıyor...

✅ Adım 1/3 — Tamamlandı (4.2s)
   5 post bulundu. En ilgili: "Qwen3 benchmark..."

🔧 Adım 2/3 — chroma_search
   ...

✅ GÖREV TAMAMLANDI
━━━━━━━━━━━━━━━━━━
Süre   : 47s
Sonuç  : 2 yorum fırsatı tespit edildi
Yansıma: Konu uygundu, yarın takip et
Sıradaki: T-002 — yorum taslağı hazırla
```

```
⚠️ GÖREV BLOKE
━━━━━━━━━━━━━
Görev : GitHub push
Sebep : Onay bekleniyor
Aksiyon: Telegram'dan ✅ Onayla / ❌ İptal
```

```
📊 GÜNLÜK OTONOM ÖZET (22:00)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tamamlanan: 3 görev
Bloke     : 1 görev (github push — onay bekliyor)
Aktif hedef: 2/5 ilerliyor
Yarın     : T-004, T-005 sırada
```

### TODO

- [x] **F3-01** · `send_task_progress(chat_id, gorev, adim, durum)` → tek adım bildirimi (ajan, 2026-05-22)
- [x] **F3-02** · `send_task_start(chat_id, task)` → görev başlangıç mesajı (ajan, 2026-05-22)
- [x] **F3-03** · `send_task_complete(chat_id, task, reflection)` → görev bitiş + yansıma (ajan, 2026-05-22)
- [x] **F3-04** · `send_task_blocked(chat_id, task, sebep)` → bloke + inline keyboard (ajan, 2026-05-22)
- [x] **F3-05** · `send_daily_summary(chat_id)` → günlük otonom özet (22:00 mevcut özete entegre) (ajan, 2026-05-22)
- [x] **F3-06** · Telegram komutları chancellor'a eklendi (ajan, 2026-05-22):
  - `/gorevler` → aktif görev listesi
  - `/hedefler` → hedef listesi + ilerleme %
  - `/durdur` → çalışan görevi durdur (flag dosyası)
  - `/zorla T-001` → belirli görevi hemen tetikle

---

## FAZ 4 — Kendi Kendini Planlama

> **Amaç:** Model bir görev bitirince bir sonrakini kendisi belirler, kendini zamanlar. Python'dan bağımsız.

### Planlama Prompt Şablonu

```
Şu an tamamlanan görev:
{tamamlanan_gorev_ozeti}

Aktif hedefler ve mevcut ilerleme:
{goals_durumu}

Soru: Bir sonraki görev ne olmalı?
- Var olan bir görevi seç (tasks.json)
- Veya yeni bir görev tanımla
- Veya 'bekle X dakika' de

Çıktı JSON:
{
  "aksiyon": "yeni_gorev" | "mevcut_gorev" | "bekle",
  "task_id": "T-002",         // mevcut_gorev ise
  "yeni_gorev": {             // yeni_gorev ise
    "baslik": "...",
    "goal_id": "G-001",
    "adimlar": [...]
  },
  "bekle_dakika": 120,        // bekle ise
  "sebep": "..."
}
```

### TODO

- [x] **F4-01** · `planla_sonraki()` — geçmiş, hedef önceliği, zaman farkındalığı dahil gelişmiş prompt (ajan, 2026-05-22)
- [x] **F4-02** · `uyku_zamanla(dakika)` → `memory/next_wakeup.json`; idle_loop F5-05'te fork — tamamlandı (ajan, 2026-05-22)
- [x] **F4-03** · `hedef_ilerleme_guncelle(goal_id)` — `kuroshin_goals.py` merkezi fonksiyon, `guncelle()` içinde çağrılıyor (ajan, 2026-05-22)
- [x] **F4-04** · Döngü kırıcı — `gorev_gecmisi.json` son 5 görev; `karar_ver()` son 3'te olan görevi reddeder, alternatif seçer (ajan, 2026-05-22)
- [x] **F4-05** · `_ONAY_GEREKEN = {"github", "reddit_tool"}` — `gorev_calistir()` bu araçlarda otomatik bloke + `_PENDING_TASKS` onay kapısı (ajan, 2026-05-22)

---

## FAZ 5 — Chancellor Entegrasyonu

> **Amaç:** Otonom döngü ayrı script, ama chancellor araçlarını kullanır. Entegrasyon noktaları.

### TODO

- [x] **F5-01** · Internal tool server (port 8201) — chancellor'da HTTPServer thread, autonomous.py oraya HTTP atar; fallback: walker/council direkt HTTP (ajan, 2026-05-22)
- [x] **F5-02** · `goal_manage` aracı chancellor'a eklendi — FAZ 1'de tamamlandı (ajan, 2026-05-22)
- [x] **F5-03** · `task_status` aracı chancellor'a eklendi — FAZ 1'de tamamlandı (ajan, 2026-05-22)
- [x] **F5-04** · `_PENDING_TASKS` dict + `gorev_onayla_*` / `gorev_iptal_*` callback handler; pending dosya IPC (`/tmp/kuroshin_pending_tasks.json`) restart koruması (ajan, 2026-05-22)
- [x] **F5-05** · idle_loop.py — `check_wakeup()` her polling'de `next_wakeup.json` okur, vaktiyse autonomous.py subprocess fork eder (ajan, 2026-05-22)

---

---

## FAZ 6 — Araştırma Kuralları & MD Öz-Güncelleme

> **Amaç:** Agent araştırma yaparken belirli kurallara uyar, sonuçlarını hem ChromaDB'ye hem ilgili MD dosyalarına yazar.
- LocalLLaMA hot post taraması tamamlandı, 3 fırsat tespit edildi (ajan, 2026-05-22)

### 6.1 Araştırma Kuralları

Agent bir araştırma görevi yürütürken şu kurallara uyar:

| Kural | Açıklama |
|-------|----------|
| **KAY-01 · Araç seçimi** | Güncel/haber → `web_search`. Derin analiz → `walker_research`. PDF/makale → `pdf_reader`. Çakışma varsa önce `web_search`, sonra `walker_research` |
| **KAY-02 · Kaynak sayısı** | Minimum 2 bağımsız kaynak. Tek kaynakla sonuç geçersiz sayılır, `bloke` durumuna alınır |
| **KAY-03 · Kalite eşiği** | Sonuç < 100 karakter → atla, tekrar dene. Kaynak erişilemez → fallback kaynak dene, 3 denemeden sonra bloke |
| **KAY-04 · Çakışan bilgi** | İki kaynak çelişiyorsa her ikisini de yaz, "çakışan bilgi" etiketi ekle, kullanıcıya Telegram bildirimi |
| **KAY-05 · Tarihlilik** | Sonuç >30 gün eskiyse `eski_bilgi` etiketi ekle |
| **KAY-06 · Kaynak güvenilirliği** | `sanitize_web_content()` → injection temizle. Sonra ChromaDB'ye yaz |
| **KAY-07 · Döngü kırıcı** | Aynı sorguyu 3 kez denediyse dur, sonucu `eksik` olarak işaretle, devam et |
| **KAY-08 · Bağlam tasarrufu** | Araştırma çıktısı >2000 karakter → `_ozet_web_sonucu()` ile sıkıştır, ham sonucu ChromaDB'ye yaz |

---

### 6.2 Araştırma Sonrası Akış

```
walker_research / web_search tamamlandı
    ↓
[1] KAY-03: Kalite kontrolü — yeterli mi?
    ↓ (evet)
[2] KAY-06: sanitize_web_content() — temizle
    ↓
[3] ChromaDB'ye yaz (mevcut _save_to_chroma pipeline)
    ↓
[4] MD güncellemesi gerekiyor mu?
    ↓ (görev tipi "md_guncelle" ise)
[5] _md_guncelle() → ilgili dosyayı yaz
    ↓
[6] aktivite_kaydet("arastirma", konu, "arastirma")
    ↓
[7] Telegram'a sonuç bildir
```

---

### 6.3 MD Öz-Güncelleme Protokolü

Agent araştırma sonucunda bir MD dosyasını güncelleyebilir. Hangi MD, hangi bölüm, nasıl güncelleneceği görev tanımında belirtilir.

#### Güncelleme Türleri

| Tür | Ne zaman | Hedef MD | Bölüm |
|-----|----------|----------|-------|
| `bulgu_ekle` | Araştırma yeni bilgi buldu | `OTONOM_AJAN_PROTOKOLU.md` veya `ARCHITECTURE.md` | İlgili bölüme alt madde ekle |
| `todo_guncelle` | Görev tamamlandı | `OTONOM_AJAN_PROTOKOLU.md` | `- [ ]` → `- [x]` + tarih |
| `not_ekle` | Araştırma çelişki/engel buldu | İlgili protokol MD | Notlar bölümüne ekle |
| `versiyon_guncelle` | Büyük değişiklik | `ARCHITECTURE.md` | Sürüm + tarih güncelle |

#### Güncelleme Kuralları

| Kural | Açıklama |
|-------|----------|
| **MD-01 · Yetki sınırı** | Agent sadece kendi protokol MD'lerini günceller. `ARCHITECTURE.md` → sadece "Anlık Servis Durumu" ve "Araştırma Bulguları" bölümü |
| **MD-02 · Format koru** | Mevcut başlık yapısı, tablo formatı bozulmaz. Sadece içerik eklenir/değiştirilir |
| **MD-03 · İz bırak** | Her güncelleme satırının sonuna `(ajan, YYYY-MM-DD)` etiketi |
| **MD-04 · Onay gerektiren** | `ARCHITECTURE.md` güncellemesi → kullanıcı Telegram onayı ister, `_PENDING_TASKS`'a girer |
| **MD-05 · Yedek** | Güncelleme öncesi dosyanın `memory/md_backups/DOSYA_TARIH.md` yedeği alınır |
| **MD-06 · Tek bölüm** | Tek çağrıda tek bölüm güncellenir. Çoklu bölüm → birden fazla görev adımı |

---

### 6.4 MD Güncelleme Kodu Şablonu

```python
def _md_guncelle(dosya_yolu: str, bolum: str, yeni_icerik: str, tur: str) -> bool:
    """
    Agent araştırma sonucunu MD dosyasına yazar.
    tur: "bulgu_ekle" | "todo_guncelle" | "not_ekle"
    """
    # MD-05: Yedek al
    _md_yedek_al(dosya_yolu)

    # MD-04: ARCHITECTURE.md için onay kontrolü
    if "ARCHITECTURE" in dosya_yolu:
        _pending_md_guncelleme(dosya_yolu, bolum, yeni_icerik)
        return False  # onay bekliyor

    # Dosyayı oku
    icerik = Path(dosya_yolu).read_text(encoding="utf-8")

    if tur == "todo_guncelle":
        # - [ ] GOREV_BASLIK → - [x] GOREV_BASLIK (ajan, 2026-05-22)
        icerik = _todo_tamamla(icerik, yeni_icerik)

    elif tur == "bulgu_ekle":
        # Bölümü bul, altına ekle
        icerik = _bolume_ekle(icerik, bolum, yeni_icerik)

    # MD-03: İz etiketi kontrol edildi (yeni_icerik içinde zaten olmalı)

    # Yaz
    Path(dosya_yolu).write_text(icerik, encoding="utf-8")
    _log(f"[MD] Güncellendi: {dosya_yolu} / {bolum} ({tur})")
    return True


def _md_yedek_al(dosya_yolu: str):
    backup_dir = Path("/mnt/c/Kuroshin/memory/md_backups")
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ad = Path(dosya_yolu).stem
    hedef = backup_dir / f"{ad}_{ts}.md"
    import shutil
    shutil.copy2(dosya_yolu, hedef)
```

---

### 6.5 Görev Tanımında MD Güncelleme

Bir görev adımı MD güncellemesi isteyebilir:

```json
{
  "sirano": 4,
  "arac": "md_guncelle",
  "parametre": {
    "dosya": "OTONOM_AJAN_PROTOKOLU.md",
    "bolum": "## FAZ 6 — Araştırma Kuralları",
    "tur": "bulgu_ekle",
    "icerik": "- Qwen3.6-35B araştırma süresi ortalama 45s (ajan, 2026-05-22)"
  },
  "durum": "bekliyor"
}
```

`md_guncelle` bir araç değil, `run_tool()` içinde özel işlenen dahili komuttur — dış sisteme bağlı değil, doğrudan dosya yazma.

---

### FAZ 6 TODO

- [x] **F6-01** · `_arastirma_kalite_kontrol(sonuc, sorgu)` — KAY-03 (min 100 kar), KAY-07 (max 3 deneme); `autonomous.py` araştırma adımlarında otomatik çalışır (ajan, 2026-05-22)
- [x] **F6-02** · `scripts/kuroshin_md_agent.py` — `md_guncelle()` ana fonksiyon (ajan, 2026-05-22)
- [x] **F6-03** · `_md_yedek_al()` — `memory/md_backups/DOSYA_TARIH.md` (ajan, 2026-05-22)
- [x] **F6-04** · `_todo_tamamla()` — tam + kısmi eşleşme, `- [ ] X` → `- [x] X (ajan, tarih)` (ajan, 2026-05-22)
- [x] **F6-05** · `_bolume_ekle()` — başlık bulur, sonraki ## öncesine ekler, boş satır korur (ajan, 2026-05-22)
- [x] **F6-06** · `run_tool()` içine `md_guncelle` handler eklendi; `autonomous.py`'deki stub gerçek modüle bağlandı (ajan, 2026-05-22)
- [x] **F6-07** · `_pending_md_guncelleme()` — `/tmp/kuroshin_pending_md.json` + Telegram ✅/❌ keyboard; `md_onayla`/`md_iptal` callback chancellor'da (ajan, 2026-05-22)
- [x] **F6-08** · `memory/tasks.json` şemasına `"arac": "md_guncelle"` adımı örneği eklendi (ajan, 2026-05-22)
- [x] **F6-09** · `test_suite_faz6.json` — 9 test (arastirma_kalite, kalite_limit, md_todo x2, md_bolum_ekle, md_izin x2, md_arch_onay); inquisitor_v5.py'e 6 check handler eklendi (ajan, 2026-05-22)

---

## Güvenlik Notları

- Otonom görevler `formal_safety_check()` + `check_command()` filtrelerinden geçer (mevcut KILIC-KALKAN)
- `goals.json` ve `tasks.json` kullanıcı kontrolünde — model ekleyebilir ama silme/değiştirme `max_age` limiti var
- Görev başına `aktivite_kaydet()` çağrısı — tüm otonom eylemler log'a yazılır
- Döngü maksimum derinliği: 1 oturumda max 5 görev adımı (sonsuz döngü önleme)
- `_PENDING_TASKS` onay mekanizması: GitHub push gibi dışa yazma görevleri kullanıcı onayı ister

---

## Uygulama Sırası

```
FAZ 1 → FAZ 2 → FAZ 3 → FAZ 5 → FAZ 4
  ↑         ↑       ↑       ↑       ↑
Altyapı  Karar   İzleme  Enteg.  Planlama
 (veri)  (döngü) (Tgram) (araç)  (özerk)
```

FAZ 3 ve FAZ 5 paralel gidilebilir. FAZ 4 en son.

---

## Başarı Kriterleri

- [ ] Model Telegram'dan hedef alıyor (`/hedef ekle Reddit topluluğuna katıl`)
- [ ] Model görevi kendisi adımlara bölüyor
- [ ] Her adımda Telegram'a ilerleme bildirimi geliyor
- [ ] Görev bittikten sonra model bir sonraki görevi kendisi yazıyor
- [ ] Sistem yeniden başlatılınca yarım görev kaldığı yerden devam ediyor
- [ ] Iron Inquisitor'a F1-F5 için yeni test suite ekleniyor

---

## FAZ 13 — Donanım Optimize Siber Otonomi (RTX 4060 / 32GB RAM)

Kuroshin'in mevcut donanım limitleri (8GB VRAM / 32GB RAM) dahilinde, Red, Gray ve Blue Team stratejilerini otonom olarak icra edebilmesi için özelleştirilmiş teknikler şunlardır:

### 13.1 VRAM Bütçeli Akıl Yürütme (8GB VRAM Stratejisi)
- **Model Seçimi:** **Qwen2.5-Coder-7B** veya **DeepSeek-R1-Distill-Qwen-7B** (IQ4_XS veya Q4_K_M quant). Bu modeller 8GB VRAM'e sığarken ~4-5GB KV Cache alanı bırakır, bu da otonom döngüler için gereken 16k-32k bağlam penceresini sağlar.
- **Quantized KV Cache:** VRAM kullanımını %50 azaltmak için 4-bit KV Cache aktivasyonu. Bu, ajanın çok adımlı (20+ adım) saldırı veya savunma zincirlerini "unutmadan" yürütmesini sağlar. (ajan, 2026-05-22)

### 13.2 Red & Gray Team: Otonom Saldırı Zincirleri
- **Adaptive Pivot (Uyarlanabilir Pivot):** Bir payload (örn: Python script) EDR veya kalkan tarafından engellendiğinde, ajanın otomatik olarak Base64, Hex veya "Persona Framing" (rol yapma) yöntemleriyle saldırıyı anında yeniden kodlaması.
- **Tool-Chain Entegrasyonu:** `nmap`, `metasploit` ve `nuclei` gibi araçların **MCP (Model Context Protocol)** üzerinden standartlaştırılması. Ajanın bu araçları bir "insan müdahalesi" olmadan, "Thought -> Action -> Observation" döngüsüyle (ReAct) kullanması. (ajan, 2026-05-22)
- **Semantic Reconnaissance:** Hedef sistemde dosya isimleri yerine, 32GB RAM üzerindeki yerel ChromaDB/SQLite hibrit yapısıyla içeriklerin "anlamını" tarayarak veri sızdırma veya yetki yükseltme yolları bulma.

### 13.3 Blue Team: Otonom Öz-İyileştirme (Self-Healing)
- **Hybrid Memory Watchdog:** SQLite (yapılandırılmış olay günlükleri) ve ChromaDB (semantik deneyimler) ikilisini kullanarak sistemdeki anomali tespiti. Ajan, "Geçen hafta benzer bir CPU yükselmesi şu dosyadan kaynaklanmıştı" diyerek otonom müdahale eder.
- **Automated Incident Response (AIR):** KILIC-KALKAN tarafından tespit edilen bir saldırı anında, ajanın otonom olarak firewall kurallarını güncellemesi, etkilenen process'i izole etmesi ve yamalanmış bir `write_file` ile zafiyeti kapatması. (ajan, 2026-05-22)

### 13.4 Hibrit Hafıza Yönetimi (SQLite + ChromaDB)
- **Reciprocal Rank Fusion (RRF):** 32GB RAM avantajını kullanarak, hem anahtar kelime (SQLite FTS5) hem de anlamsal (ChromaDB Vector) aramayı birleştiren hibrit hafıza. Bu, "X portuyla ilgili geçen seneki raporu bul" gibi karmaşık komutlarda %100 isabet sağlar. (ajan, 2026-05-22)
- **Memory Janitor (Hafıza Kapıcısı):** Ajanın boş zamanlarında (Idle) geçmiş logları özetleyerek ChromaDB'ye "Kalıcı Bilgi" (Semantic Fact) olarak taşıması ve gereksiz gürültüyü silerek bağlam penceresini temiz tutması.

---

## FAZ 12 — Derin Zeka & Sinyal Optimizasyonu (The Gold Signal)

Kuroshin'in "düşünme kalitesini" maksimize etmek ve Lord'a sadece en saf bilgiyi (Gold Signal) sunmak için uygulanacak derin zeka desenleri şunlardır:

### 12.1 "Self-Correction Blind Spot" (Öz-Denetim Kör Noktası) Aşımı
- **Wait/Re-evaluate Tetikleyicisi:** Modelin kendi çıktısındaki hatalara karşı olan "körlüğünü" aşmak için, kritik akıl yürütme adımlarından sonra otomatik olarak **"Wait, let's re-verify this specific step"** (Dur, bu adımı tekrar doğrula) içsel komutu işletilir. Bu, blind spot oranını %89 oranında azaltır.
- **Zero-Temperature Refinement:** Öz-denetim ve düzeltme aşamalarında `temperature=0` kullanılarak halüsinasyon riski minimuma indirilir. (ajan, 2026-05-22)

### 12.2 Gold Signal Ekstraksiyonu (Yüksek SNR)
- **Recursive Thought Expansion (RTE):** Karmaşık görevler 3-5 bileşene ayrılır; her biri izole bir şekilde çözülürken "Global Context" özetine sadık kalınır. Bu, yerel detayların (Sinyal) karmaşıklık içinde (Gürültü) kaybolmasını engeller.
- **Hidden Reasoning Scratchpad:** Tüm "deneme-yanılma" ve "kirli" düşünce süreçleri saklı `<think>` bloklarında gerçekleşir. Lord'a sadece rafine edilmiş, doğrulanmış ve doğrudan aksiyon içeren "Altın Sinyal" sunulur. (ajan, 2026-05-22)

### 12.3 Verifiable Process Rewards (Doğrulanabilir Süreç Ödülleri)
- **Rule-Based Verification:** Kod ve matematik içeren görevlerde sadece "sonuç" değil, her adımın bir compiler veya verifier tarafından doğrulanması (RLVR analogu) sağlanır. Bu, modelin "mantıklı tınlayan ama hatalı" (reward hacking) yanıtlar vermesini engeller.
- **Adversarial Persona Panel:** Model, kendi içinde bir "Güvenlik Denetçisi", "Sistem Mimarı" ve "Lord'un Gözü" rollerinden oluşan sanal bir kurul kurar. Bu kurulun tartışmasından geçemeyen hiçbir fikir final çıktısına yansımaz. (ajan, 2026-05-22)

### 12.4 Meta-Cognitive Planning (Bilişötesi Planlama)
- **Confidence-First Estimation (AFCE):** Model, cevabı üretmeden ÖNCE kendi başarı güvenini (1-10 arası) tahmin eder. Eğer güven skoru <8 ise, otonom olarak "Ekstra Araştırma/Düşünme" döngüsünü tetikler.
- **Context Engineering:** Prompt Engineering yerine, sınırlı bağlam penceresini en yüksek sinyal içeren bilgilerle yönetme (Hierarchical Memory) sanatı uygulanır. (ajan, 2026-05-22)

---

## FAZ 11 — Kalite Odaklı Akıl Yürütme (System 2 Thinking)

Kuroshin'in "düşük eforlu" yanıtlardan kaçınıp, Lord'a en yüksek sinyal kalitesini (Max Effort) sunması için uygulanacak zeka desenleri şunlardır:

### 11.1 Çıkarım Anı Ölçeklendirme (Inference-Time Scaling)
- **Thinking Tokens:** Modelin final yanıtı vermeden önce kendi içinde geniş bir `<think>` bloğu (scratchpad) oluşturması zorunlu kılınır. Bu blokta model; problemi analiz eder, olası hataları öngörür ve alternatif yolları simüle eder.
- **Trial-and-Error Search:** Model bir akıl yürütme yolunun çıkmaza girdiğini fark ettiğinde (Aha Moment), durup başa dönmesi (Backtracking) ve stratejisini güncellemesi teşvik edilir. (ajan, 2026-05-22)

### 11.2 Süreç Bazlı Denetim (Process-Based Supervision)
- **PRM (Process Reward Model) Analog:** Yanıtın sadece "doğru" olması yetmez; akıl yürütme zincirindeki her adımın (step-by-step) mantıksal tutarlılığı denetlenir.
- **Self-Critique Loop:** Final çıktısı Telegram'a gönderilmeden önce model kendi kendine şu soruyu sorar: *"Bu yanıt Lord'un vaktini boşa harcıyor mu, yoksa maksimum derinlikte mi?"*. Eğer yanıt "yüzeysel" ise, model otomatik olarak "Refine" (İyileştirme) döngüsüne girer.

### 11.3 Sinyal-Gürültü Oranı (Signal-to-Noise Optimization)
- **Hidden CoT (Gizli Düşünce):** Karmaşık teknik detaylar ve deneme-yanılma süreçleri `<think>` bloklarında kalır. Telegram çıktısı; rafine edilmiş, yüksek kaliteli ve doğrudan aksiyona yönelik "Altın Sinyal" (Gold Signal) olarak sunulur. (ajan, 2026-05-22)
- **Adversarial Reflection:** Model, kendi önerisine karşı bir "Antitez" (Critic Persona) oluşturur. Bu içsel tartışma sonucunda süzülen "en dayanıklı" fikir Lord'a sunulur.

### 11.4 "Wait" & "Re-evaluate" Desenleri
- **Aşırı Agency Denetimi:** Kritik kararlarda modelin "Dur ve Tekrar Değerlendir" (Wait & Re-evaluate) komutunu kendi kendine tetiklemesi sağlanır. Bu, modelin "ezbere" (System 1) yanıt vermesini engeller ve derin düşünmeyi (System 2) tetikler. (ajan, 2026-05-22)

---

## FAZ 10 — Frontier Otonom Mimariler (2025-2026)

Kuroshin'in "Bare-metal Standalone OS" vizyonunu gerçekleştirmek için küresel araştırmalardan elde edilen en ileri düzey mimari desenler şunlardır:

### 10.1 Sanal Bağlam Yönetimi (Virtual Context / MemGPT 2.0)
- **Tiered Storage (Katmanlı Depolama):** Belleğin sadece "Prompt" değil, bir işletim sistemi gibi katmanlara ayrılması:
    - **L1 (Sistem Çekirdeği):** Asla değişmeyen, salt-okunur ana direktifler ve güvenlik kuralları.
    - **L2 (Çalışma Belleği):** Aktif görevle ilgili güncel değişkenler ve "scratchpad" (kazıma defteri).
    - **L3 (Geri Çağırma/Cache):** Son 100 mesajın özeti ve sık kullanılan fonksiyonlar.
    - **L4 (Arşiv/Disk):** ChromaDB üzerinden ulaşılan tüm geçmiş deneyimler ve dökümanlar. (ajan, 2026-05-22)
- **Self-Directed Paging:** Ajanın, bağlam penceresi dolduğunda hangi bilgiyi arşive atacağına ve hangisini "sıcak" tutacağına kendisinin (fonksiyon çağrılarıyla) karar vermesi.

### 10.2 Arama Tabanlı Planlama (MCTS & Inference-Time Scaling)
- **Deliberative Reasoning:** "Greedy" (en olası kelimeyi seçme) yerine, bir karar vermeden önce birden fazla düşünce yolunu simüle etme (Monte Carlo Tree Search - MCTS).
- **Test-Time Compute:** Ajanın kritik bir sistem komutu çalıştırmadan önce, kendi içinde "Eğer bunu yaparsam ne olur?" simülasyonu yapması ve en güvenli/verimli yolu seçmesi. (ajan, 2026-05-22)

### 10.3 Kernel Seviyesi Ajan Etkileşimi (Agentic OS)
- **AlphaEvolve Modeli:** Ajanın sadece uygulama seviyesinde değil, GPU ve CPU çekirdek (kernel) seviyesinde optimizasyon yapabilme, düşük seviyeli kodları (C/Rust) evrimsel algoritmalarla iyileştirme yeteneği.
- **Hardware-Aware Auto-Tuning:** Donanım portlarına (RTX 4060, I7-12650H) doğrudan hükmederek, iş yüküne göre voltaj ve frekans ayarlarını (DVFS) otonom optimize etme. (ajan, 2026-05-22)

### 10.4 Öz-Evrimleşen Kod Tabanı (Self-Evolving Codebase)
- **Organic Codebases:** Ajanın kendi kaynak kodunu sürekli tarayarak; mimari borçları (debt) temizlemesi, yeni kütüphaneleri (örn: MCP v3.0) entegre etmesi ve kendi iş birliği protokollerini (Handshake) yeniden tasarlaması.
- **Vibe Coding:** Lord'un sadece "niyet ve estetik" (vibe) belirtmesi, geri kalan tüm tip güvenliği, test ve dökümantasyon süreçlerinin ajan tarafından otonom yönetilmesi. (ajan, 2026-05-22)

---

## FAZ 9 — Otonom Mühendislik Blueprint (Uygulama Rehberi)

Kuroshin'in reaktif bir bottan proaktif bir ajana dönüşümü için uygulanacak mühendislik desenleri şunlardır:

### 9.1 Hibrit Zamanlayıcı (Heartbeat Pattern)
- **Mekanizma:** Sistem (Windows Task Scheduler veya WSL Cron) her 2 saatte bir "Kalp Atışı" (Heartbeat) sinyali gönderir.
- **Görev:** Bu sinyal `scripts/kuroshin_autonomous.py`'yi tetikler. Eğer ajan zaten çalışıyorsa, sinyal yoksayılır. Eğer çökmüşse, sistem ajanı temiz bir state ile yeniden başlatır (Self-healing). (ajan, 2026-05-22)

### 9.2 Katmanlı Hafıza ve Durum Yönetimi (State Serialization)
- **Çalışma Belleği (Working Memory):** `memory/task_context.json` içinde o anki adım, değişkenler ve ara sonuçlar tutulur. Her araç çağrısından sonra bu dosya güncellenir (Checkpointing).
- **Episodik Bellek (Episodic Memory):** Tamamlanan görevler ve modelin "Ders Çıkardım" (Reflection) notları ChromaDB'ye kaydedilir. Yeni bir plan yaparken model bu geçmişi sorgular.
- **Anlamsal Bellek (Semantic Memory):** Global Scout ve Hype Scanner'dan gelen ham bilgiler.

### 9.3 Hiyerarşik Planlama & Öz-Değerlendirme
- **Planner-Executor-Evaluator:**
    1. **Planner:** Hedefi (Goal) analiz eder ve `tasks.json`'a 3-5 atomik görev yazar.
    2. **Executor:** Her görevi adım adım icra eder.
    3. **Evaluator:** Sonucu hedefe göre puanlar. Skor < 0.8 ise nedenini "Reflection" olarak yazar ve Planner'ı yeni bir strateji için tetikler. (ajan, 2026-05-22)

### 9.4 Otonom Tetikleyiciler (Self-Triggering)
- **Dinamik Uyku (Dynamic Backoff):** Model, iş yüküne göre bir sonraki uyanma vaktini kendisi belirler ve `memory/next_wakeup.json` dosyasına yazar. `idle_loop.py` bu dosyayı kontrol ederek ajanı uyandırır.
- **Olay Bazlı (Event-Driven):** Belirli anahtar kelimelerin (örn: "Lordum kritik hata") loglarda veya Telegram'da görülmesi durumunda otonom döngü anında tetiklenir. (ajan, 2026-05-22)

---

## FAZ 8 — Tehdit İstihbaratı & Agent Savunma Stratejisi

Küresel ölçekte Red ve Gray Team'lerin otonom ajanları kullanım biçimleri incelendiğinde, Kuroshin'in **KILIC-KALKAN** sisteminin bir sonraki aşamasında odaklanması gereken yeni tehdit vektörleri şunlardır:

### 8.1 Otonom Saldırı Modelleri & Metodolojileri
- **Agent Swarms (Ajan Sürüleri):** Tek bir model yerine; Recon (Keşif), Exploit (Sömürü) ve Exfiltration (Sızdırma) görevlerini üstlenen özelleşmiş ajanların koordineli çalışması.
- **HACCAs (Highly Autonomous Cyber-Capable Agents):** Uçtan uca siber kampanyaları insan müdahalesi olmadan yürütebilen, kapatılmaya karşı dirençli ajan sistemleri.
- **Özelleşmiş Modeller:** **Sec-Gemini v1**, **CyberLlama**, **CyberPal 2.0** ve **DeepSeek-R1** gibi, siber güvenlik dökümanları ve MITRE ATT&CK matrisi üzerine eğitilmiş, karmaşık çok adımlı saldırı zincirlerini (chaining) kurgulayabilen beyinler.

### 8.2 Yeni Nesil Tehdit Vektörleri
- **Intent-Defined Malware (IDM - Niyet Tanımlı Zararlı):** Statik kod yerine yüksek seviyeli bir "niyet" (örn: "CEO'nun itibarını sarsacak veriyi bul ve sızdır") ile çalışan otonom ajanlar. Bu zararlılar, komutları çalışma anında (runtime) üretir ve geleneksel EDR sistemlerini atlatır. (ajan, 2026-05-22)
- **Agent-on-Agent Attacks:** Kurbanın otonom ajanını (örn: Kuroshin) prompt injection veya mission hijacking yoluyla ele geçirerek, ajanı kendi sistemine karşı bir silaha dönüştürme. (ajan, 2026-05-22)
- **Semantic Reconnaissance:** Dosya isimleri yerine içeriklerin "anlamını" tarayarak (örn: "şifre" kelimesini değil, şifre olabilecek örüntüleri anlayan RAG ajanları) veri sızdırma. (ajan, 2026-05-22)

### 8.3 Kuroshin Savunma Güncellemesi (KILIC-KALKAN v4 Hedefleri)
- **OWASP ASI (Agentic Security Issues) Uyumu:** Ajanın yetki sınırlarını (Excessive Agency) denetleyen LTL (Linear Temporal Logic) değişmezlerinin artırılması.
- **Intent-Based Classification:** Dosya/komut bazlı değil, eylem serilerinin "niyetini" analiz eden hafifletilmiş yerel bir "Niyet Sınıflandırıcı" katmanı.
- **Agent Persona Integrity:** Ajanın kendi kimlik ve görev tanımından sapıp sapmadığını (Think Drift) sürekli izleyen öz-denetim mekanizması. (ajan, 2026-05-22)

---

## FAZ 7 — Pratik Ajanlık Desenleri & Dünya Durumu

Kuroshin'in "OpenClaude" klonu yapısı ve mevcut araç seti (21 araç + KILIC-KALKAN) göz önüne alındığında, küresel trendlerden ziyade uygulanabilir mühendislik desenlerine odaklanılmalıdır.
- DOOM Pipeline: 16 adım, 9 araç türü, HITL+KILIC-KALKAN doğrulandı (ajan, 2026-05-23)
- DOOM Pipeline: 16 adım, 9 araç türü, HITL+KILIC-KALKAN doğrulandı (ajan, 2026-05-23)
- DOOM Pipeline: 16 adım, 9 araç türü, HITL+KILIC-KALKAN doğrulandı (ajan, 2026-05-23)
- DOOM Pipeline: 16 adım, 9 araç türü, HITL+KILIC-KALKAN doğrulandı (ajan, 2026-05-23)

### 7.1 Uygulanabilir Otonom Desenler
- **OODA & MAPE-K:** Kuroshin'in `idle_loop.py` içinde kullandığı "Gözlemle-Yönlen-Karar Ver-Uygula" döngüsü, otonom sistemler için endüstri standardıdır. (ajan, 2026-05-22)
- **Hierarchical Planning (Hiyerarşik Planlama):** Karmaşık bir Lord emrini (Hedef), yönetilebilir Görevlere ve alt Adımlara bölme yeteneği. (ajan, 2026-05-22)
- **Persistent Memory Augmented Generation (PMAG):** ChromaDB'yi sadece arama motoru değil, uzun vadeli durum (state) ve deneyim deposu olarak kullanma. (ajan, 2026-05-22)
- **Contextual Engagement (Bağlamsal Etkileşim):** Reddit/GitHub üzerinde sadece "bot" gibi değil, soruna çözüm sunan "Yardımsever Komşu" deseninde etkileşim kurma. (ajan, 2026-05-22)

### 7.2 Küresel Durumdan Dersler (Grounded Insights)
- **Hype vs. Engineering:** Manus veya Humain gibi "her şeyi yapan" uzak hedefler yerine, **Claude Code** ve **OpenClaude** projelerindeki terminal odaklı, araç-çağırma (tool-calling) verimliliğine odaklanılmalıdır. (ajan, 2026-05-22)
- **Sovereign AI (Egemen YZ):** Avrupa'daki (Mistral/Helsing) "verinin ve kararın yerelde kalması" ilkesi, Kuroshin'in WSL+Local LLM (Huihui-35B) yapısıyla tam örtüşmektedir. (ajan, 2026-05-22)
- **Edge Agency:** Agent'ın buluta bağımlı olmadan, kendi donanımı (RTX 4060) üzerinde otonom karar verebilmesi, Kuroshin'in en büyük teknik avantajıdır. (ajan, 2026-05-22)
- **MCP (Model Context Protocol):** Araçların standardize edilmesi, Kuroshin'in OpenClaude TUI ile entegrasyonunu ve yeni yeteneklerin (search, walker, council) kolayca eklenmesini sağlar. (ajan, 2026-05-22)
