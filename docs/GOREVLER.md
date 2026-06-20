# Kuroshin OS — Aktif Görev Masası
**Son güncelleme:** 20 Haziran 2026 (sohbet-52)

> Bu dosya AKTIF görevleri tutar. Tamamlanan dalga geçmişi DEVAM.md'nin alt bölümlerinde.

---

## 🔄 KUROWATCH — Aktif Görevler (öncelik sırası)

| # | Görev | Dosyalar | Durum |
|---|---|---|---|
| [1] | manga.py Madara domains | backend/downloader/manga.py | ✅ TAMAM (82af85d) |
| [2] | Site sıralama — chapter count bazlı | app.js renderDetailSites() | bekliyor |
| [3] | In-detail okuma/izleme butonu (overlay iframe) | index.html + app.js _epHtml | bekliyor |
| [4] | Arka planda indirme + popup (%50 toast) | player.js + app.js toast | bekliyor |
| [5] | enrich_site_urls.py — dizibox + hdfilmcehennemi + merlintoon | scripts/enrich_site_urls.py | bekliyor |
| [6] | stream_finder.py — dizibox + hdfilmcehennemi embed | downloader/stream_finder.py | bekliyor |
| [7] | audit_all_media.py + dead site yönetimi | scripts/audit_all_media.py | bekliyor |

**Detay:** Her görevin tam açıklaması → `kurowatch/docs/DEVAM.md`

---

## 📊 DALGA DURUMU

| Dalga / Modül | Durum | Son Commit |
|---|---|---|
| DALGA 1-5 | ✅ TAMAMLANDI | — |
| DALGA-6 Market Master v11.33.4 | ✅ TAMAMLANDI | `6f22207` |
| KuroRecon v1.0.0 (Fiyat Alarm) | ✅ TAMAMLANDI | `842263f` |
| FloatingUI FAZ-1~5 | ✅ TAMAMLANDI | `93c45df` |
| Iron Inquisitor 97/97 %100 | ✅ TAMAMLANDI | `6f22207` |
| KuroWatch v1.0.0 | 🔄 AKTİF — sohbet-52 devam | `82af85d` |

---

## ⏸️ Askıya Alınan Görevler

- **FAZ-B Reddit** — askıda (Lord kararı bekliyor)
- **MODEL-01~05** — Qwen3-30B-2507 geçişi askıda
- **FloatingUI zoom artifact (#7)** — askıda
- **Tinder-swipe nav** — KuroWatch gelecek FAZ (Lord kararı)
- **Manga çeviri "Düzelt" butonu** — KuroWatch FAZ-5 kalan

---

## 📚 MD Rehberi — Hangi Dosya Ne İçin

| Dosya | Amaç | Ne Zaman Okunur |
|---|---|---|
| `docs/DEVAM.md` | Kuroshin ana handoff + en son yapılanlar | **Her yeni sohbet BAŞINDA** (zorunlu) |
| `docs/GOREVLER.md` | Aktif görev takibi + dalga durumu | Görev durumu kontrol ederken |
| `docs/OTONOM_ALISVERIS_PROTOKOLU.md` | Market Master pipeline protokolü | Market Master sohbetlerinde (referans) |
| `kurowatch/docs/DEVAM.md` | KuroWatch handoff + sıradaki görevler | KuroWatch sohbeti başında (zorunlu) |
| `kurowatch/docs/YAPI.md` | KuroWatch mimari + API kararları | Mimari/DB karar alırken |
| `kurowatch/docs/FEATURE_MAP.md` | Özellik checklist + FAZ haritası | Özellik durumu kontrol ederken |
| `kurowatch/docs/TEST_PLAN.md` | Test senaryoları + T01-T06 planı | Test koşarken |
| `CLAUDE.md` (kök) | Claude direktifleri | Otomatik okunur, değiştirme |
| `docs/archive/` | Tamamlanan/eski belgeler | Tarihsel referans (günlük kullanım yok) |
