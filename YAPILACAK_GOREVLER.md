# Kuroshin OS - Acik Gorevler
**Son Guncelleme:** 17 Mayis 2026 (v8.3 - Feedback→Mood + Yokluk Ozeti + Bat Temizligi)

Sadece tamamlanmamis isler burada. Tamamlananlar MASTER_ROADMAP'e tasindi.

---

## KRITIK / ACIK

- [x] **Model degerlendirmesi (#13)** - KARAR: Qwen3-8B-abliterated Q5_K_M (bartowski/mlabonne). `start_llama.sh` + tum agent'lar guncellendi. (17 Mayis 2026)
- [x] **Model indirme & gecis** - Indirildi (5.85GB, 2m33s). `start_llama.sh` + tum agent + LiteLLM + TUI guncellendi. TUI `qwen3-abliterated` dogrulandi. (17 Mayis 2026)
- [x] **TUI `/model` <-> backend senkronu** - `switch_model.py` tek merkez yapildi. TUI picker yerel katalogu buradan okur; model secince llama-server restart + TUI state + sonraki boot ayni kaynaktan senkronize olur. (17 Mayis 2026)
- [x] **Iron Inquisitor - Qwen3 dogrulamasi** - 1/1 PASS %100. reminder-tool-01 gecti. (17 Mayis 2026)
- [x] **Eski model temizligi** - Gemma4 (5.1G) + Qwen2.5-Coder-1.5B + Thinking-Claude-1.2B + bluey8b/eve4b/ibm_coder/peca + Qwen3.6-35B silindi. Kalan: yeni beyin + qwen_hf (finetune). (17 Mayis 2026)
- [ ] **100 onayli kayit -> ilk LoRA egitimi** - Pipeline hazir, kayit henuz dolmadi. Sistem kendi kendine biriktirecek.
- [x] **finetune/ klasoru silindi** - 15GB geri kazanildi. README kaldi. (17 Mayis 2026)
- [ ] **avatar_bridge key dogrulamasi** (PASIF) - Mate-Engine acikken `Kuroshin_Blendshapes.json`'u kontrol et. Key'ler dogru mu?
- [x] **memory-add-query-01 validation hatasi** - `collection` -> `collection_name` duzeltildi. `tool_called` mantigi validation error'i da FAIL sayiyor. (17 Mayis 2026)

---

## FAZ 7.2 — OTONOM CANLILIK (YENİ VİZYON)

### Tier 1 — Temel (hemen yapılabilir, altyapı hazır)
- [x] **Idle Probe döngüsü** — OODA heartbeat: 2 saatte bir tetikle, sessizlik/mood/enerji'ye göre Araştır/Paylaş/Düşün kararı. `_idle_probe()` + `/probe` test komutu + `/energy` durum komutu. **Test geçti: boot'ta 156dk sessizlik tespiti + web_search çalıştı. Energy budget harcandı (2/5).** (17 Mayıs 2026)
- [x] **Geri bildirim inline keyboard** — Probe araştırması sonrası [👍 İlginç] [👎 Sıkıcı] [🔍 Devam araştır] butonu. `callback_query` handler + `_feedback_isle()` + `feedback.json` yazımı. (17 Mayıs 2026)
- [x] **İlgi profili öğrenimi** — `_feedback_isle()`: 👍 → `guclu_tepki_verilen` başa ekle, 👎 → `zayif_tepki_verilen`'e ekle + güçlüden çıkar. `_konu_sec()` zayıfları filtreler. (17 Mayıs 2026)
- [x] **Rüya yorum + paylaşım** — `_get_dream_yorum()`: sabah 05-10 arası LLM ile tam yorum üretip selamlamaya ekle. 10-14 arası referans. (17 Mayıs 2026)

### Tier 2 — Orta (1-2 gün iş)
- [x] **Günlük keşif özeti** — Gece 22:00 polling loop'ta tetiklenir: `_gunluk_kesif_ozeti()` bugünkü [PROBE] kayıtlarını toplar, model özetler, Telegram'a gönderir. (17 Mayıs 2026)
- [x] **Merak listesi** — ChromaDB `merak_listesi` koleksiyonu: `_merak_ekle()` / `_merak_listeden_konu()`. Araştırma sonundaki soru otomatik ekleniyor. `_konu_sec()` önce buradan çeker. (17 Mayıs 2026)
- [x] **Deneyim günlüğü** — `logs/deneyimler/YYYY-MM-DD.md`: her araştırma `_deneyim_kaydet()` ile tarihli dosyaya yazılıyor. (17 Mayıs 2026)

### Tier 3 — İleri (karmaşık, zaman ister)
- [x] **Sessizlik cezası + ilgisizlik reaksiyonu** — 6+ saat sessizlik → `_ooda_karar` "ilgisizlik" döndürür → model içten mesaj yazar, son konu `zayif_tepki_verilen`'e eklenir, konu listesinden silinir. (17 Mayıs 2026)
- [x] **Davranış öğrenimi** — `_feedback_isle()`: 👍 → konu `guclu_tepki_verilen` listesi başına, 👎 → `zayif_tepki_verilen`'e. `_konu_sec()` zayıfları filtreliyor. Pattern otomatik oluşuyor. (17 Mayıs 2026)
- [x] **Kullanici inaktifken otonom mod** — Probe zaten 2 saatte bir araştırıyor. Sessizlik >4 saat ise selamlama mesajında "Yokluğunuzda şunları araştırdım" özeti gösteriliyor. (17 Mayis 2026)

### Tier 4 — Araştırma & Şema Geliştirme (süregelen görev)
- [x] **Yapay zeka canlılık deneyleri keşfi** — Her 7 günde bir `_canlilik_arastir()` tetikleniyor. 5 sorgu havuzu, Walker→web_search fallback, `logs/schema_kesfler/` + `memory/schema_onerileri.json` + Telegram bildirimi. (17 Mayis 2026)

---

## DEVAM EDEN - RUH (FAZ 7.1)

- [x] Chancellor system prompt derinlestirme (v2.1)
- [x] ChromaDB direkt hafiza (`_get_chroma_context()`)
- [x] Proaktif idle_loop v1.4 - raporlar + merak + sessizlik decay + proaktif sohbet
- [x] Durum farkindaligi - mood -> system prompt injection
- [x] Dream Engine v1.0 - gece ruya sentezi, `logs/dreams/`
- [x] Emote sistemi - 10 duygu x 5 emote havuzu
- [x] Internet farkindaligi - `internet_status` tool + system prompt `{internet_line}`
- [x] Ilgi skoru her mesajda guncelleme (slash komutlar dahil)
- [x] Dream Engine sabah referansi - `_get_dream_ref()` selamlama mesajina eklendi
- [x] Emote selamlama - `_selamlama()` dominant mood'a gore emote seciyor
- [x] ChromaDB ani kaydi - Her yanit `_save_to_chroma()` ile arka planda kaydediliyor
- [x] system_info tool - Saat/lokasyon/PC tahmini/kullanici profili
- [x] **Iron Inquisitor v5.1 - 23/23 PASS %100** (17 Mayis 2026)
- [x] **Iron Inquisitor v5.2 - Secici Calistirma** - `--only`, `--category`, `--skip-passed`, `--no-telegram` flag'leri eklendi. Sadece basarisiz testleri yeniden calistirabilir. (17 Mayis 2026)
- [x] Dream Engine sabah referansi chancellor entegrasyonu - `_get_dream_yorum()` sabah 05-10 tam yorum, `_get_dream_ref()` 10-14 referans. (17 Mayis 2026)
- [x] Odul/ilgi algoritmasi persist - feedback mood_state.json'a kalici yaziliyor. (17 Mayis 2026)
- [x] ChromaDB haftalik ozet - Pazar 23:00 polling loop'tan tetikleniyor. (17 Mayis 2026)
- [x] **RAG kontaminasyonu + sohbet kalitesi** - 4 adim tamamlandi (17 Mayis 2026):
  - A) fix_chroma.py genisleti: walker/port/servis kaliplari da temizleniyor
  - B) Sohbet sorularinda RAG kapandi: `_is_conversational` → `chroma_ctx = ""`
  - C) `_save_to_chroma` filtresi: tool ciktisi kaliplari iceriyorsa kaydetme
  - D) THINK turu Turkce zorlama: prompt basi "SADECE TÜRKÇE YAZ" satirina alindi
  - fix_chroma.py WSL'de calistirmak gerekiyor (mevcut kotu kayitlari temizler)
- [x] **TUI acilmiyor** - boot_gauntlet_notify.sh Nuclear Search `/search?q=test` asiyordu -> `/health` duzeltildi. (17 Mayis 2026)
- [x] **ChromaDB No module named** - Chancellor venv'siz baslatiliyordu -> `source /root/kuroshin/venv/bin/activate` bat'a eklendi. (17 Mayis 2026)
- [x] **Hallucination: hava cok guzel** - ChromaDB kotu kayit kontaminasyonu + RAG disclaimer eklendi. (17 Mayis 2026)
- [x] **Karakter kirilmasi: Ben yapay zekayim** - System prompt Turkce yeniden yazildi v8.0. (17 Mayis 2026)
- [x] **GPU uyari esigi cok dusuk** - 80°C -> 85°C, `>=` -> `>` operatoru, cooldown 600->900s. (17 Mayis 2026)

---

## AVATAR / ANIMASYON

- [ ] **Mixamo erkek animasyon paketi** - `adobe.com/products/mixamo` -> ucretsiz hesap -> erkek karakter sec -> FBX export -> `C:\Kuroshin\kuroshin avatar vrm\Mate-Engine\Animations\` -> Custom Dance Player'a yukle.
- [ ] **MMD animasyon konverteri** - `.vmd` formatindaki MMD animasyonlarini `.fbx`'e cevir -> Mate-Engine Custom Dance Player. Arac: Blender + `mmd_tools`.
- [x] **avatar_bridge.py aktiflestir** - v2.0 tamamlandi. Dosya IPC: `mood_state.json` -> `Blendshapes/Kuroshin_Blendshapes.json`. Mate-Engine BlendshapeManager her 0.75s okur, BepInEx gerektirmez. `Kuroshin.bat` [6/6]'ya eklendi.
- [ ] **avatar_bridge key dogrulamasi** - Mate-Engine acikken `Kuroshin_Blendshapes.json`'u kontrol et. Key'ler `Body:Fun`, `Body:Joy` vb. mi yoksa mesh adi farkli mi? Gerekirse `DUYGU_EXPR` dict'ini guncelle.

---

## TAMAMLANDI (SON OTURUM)

- [x] **fix_chroma.py çalıştırıldı** — 8 kayıttan 3 kötü kayıt silindi (sohbet pattern + prompt leak), 5 temiz kayıt kaldı. (18 Mayıs 2026)
- [x] **Proaktif tetik mekanizması düzeltildi** — `saat % 3 != 0` kontrolü kaldırıldı, `PROAKTIF_COOLDOWN` (3s) yeterli. `idle_loop.py` (18 Mayıs 2026)
- [x] **Merak eşiği düşürüldü** — `0.6 → 0.3`, araştırma döngüsü artık tetiklenebilir. `idle_loop.py:386` (18 Mayıs 2026)
- [x] **Günlük otonom araştırma** — Sabah 10:00 `_gunluk_otonom_arastirma()`: 2 konu seç → walker/web_search → ChromaDB + deneyim günlüğü + Telegram bildirimi. `chancellor.py` (18 Mayıs 2026)
- [x] **Öz-yansıma döngüsü** — Gece 23:00 `_oz_yansima()`: deneyim günlüğü oku → Qwen3 meta-bilişsel yorum → Telegram + ChromaDB. `chancellor.py` (18 Mayıs 2026)
- [x] **idle_loop.py yeniden başlatıldı** — PID 30698 aktif, sağlıklı. (18 Mayıs 2026)
- [x] **Dream Engine → Chancellor tam entegrasyon** — 4 düzeltme (18 Mayıs 2026):
  - `dream_engine.py`: rüya ChromaDB'ye kaydediliyor → `chroma_search("rüya")` artık bulur
  - `_think_turn`: rüya önizlemesi iç ses promptuna enjekte ediliyor
  - `_selamlama`: rüya referansı 14:00 sınırı kaldırıldı, gün boyu aktif
  - `dream_engine.py` servisi başlatıldı: PID 30780

---

## DUSUK ONCELIK / ILERIDE

- [x] **Boot Telegram asama bildirimi** - `boot_notify.sh` zaten calisiyor, [0/6]->[6/6] ilerleme cubugu Telegram'a gidiyor.
- [x] **eval_feedback_loop.py Kuroshin.bat entegrasyonu** - Menu [9] eklendi: test-only / auto-apply / tek dongu secenekleri. (17 Mayis 2026)
- [x] **Skor esigi Telegram bildirimi** - Basarisiz test orani >%30 -> ozel Telegram alarmi. `inquisitor_v5.py`'ye eklendi. (17 Mayis 2026)
- [x] **DeerFlow 2.0** - Subprocess bagimliligi kaldirildi. Inline: DuckDuckGo + Crawl4AI + Crawlee fallback + ChromaDB cache + coklu kaynak. (17 Mayis 2026)
