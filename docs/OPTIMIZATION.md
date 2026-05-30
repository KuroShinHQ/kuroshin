# Kuroshin Yapı & Dökümantasyon Optimizasyon Raporu (v1.8)
**Tarih:** 23 Mayıs 2026
**Durum:** ✅ KAPANDI — Dosya yeniden adlandırma planı KRİTİK KIRILMA RİSKİ nedeniyle kalıcı olarak iptal edildi.

> ## Neden İptal Edildi — Kırılma Riski Analizi
>
> Spy analizi (lsof + strace, 23 Mayıs 2026) sonrası tespit edildi:
>
> | Kırılacak Bileşen | Etkilenen Dosya Sayısı | Kurtarma Süresi Tahmini |
> |-------------------|------------------------|-------------------------|
> | Iron Inquisitor test suite'leri (mutlak path) | 8 JSON dosyası, 61 test | 2-3 saat |
> | Shell start scriptleri (`start_*.sh`) | 10+ script | 1 saat |
> | Bat PowerShell komutları | 15+ satır | 30 dk |
> | `.mcp.json` + `.mcp.wsl.json` | 2 config | 15 dk |
> | Python `sys.path.insert` + `Path()` referansları | 50+ satır (sadece chancellor.py) | 3-4 saat |
> | **Toplam risk** | **~100 referans** | **~7-8 saat çalışma + test** |
>
> **Karar:** Fayda (sadece görsel/estetik isimlendirme değişikliği) < Maliyet (7-8 saat + sistem kararsızlığı riski).
> **Mevcut isimlendirme sonsuza kadar korunacak.**

---

## FAZ 0 — Runtime Dependency Discovery (Gözlem Aşaması)

Sistemin canlı dosya bağımlılıklarını tespit etmek için "İzleyici (Observer)" araçları:

- **Python Spy (`kuroshin_spy.py`):** Modül yüklemelerini ve dosya açma işlemlerini runtime'da yakalar.
- **WSL Observer (`wsl_spy.sh`):** İşletim sistemi seviyesinde `strace` ile dosya erişimlerini loglar.
- **Log Yolu:** `data/logs/discovery/`

### ⚠️ Doğru Kullanım (23 Mayıs 2026 düzeltmesi)

`kuroshin_spy.py` **tek başına çalıştırılamaz** — hedef scripte import edilmesi gerekir:

```bash
# Python Spy — chancellor.py'yi izle:
wsl -- bash -lc "source /root/kuroshin/venv/bin/activate && cd /mnt/c/Kuroshin && python3 -c \"import scripts.kuroshin_spy; exec(open('agents/kuroshin_chancellor.py').read())\""

# WSL Spy (strace) — komut argümanı zorunlu:
wsl -- bash -lc "source /root/kuroshin/venv/bin/activate && cd /mnt/c/Kuroshin && bash scripts/wsl_spy.sh python3 agents/kuroshin_chancellor.py"
```

**Durum:** 23 Mayıs 11:21 — `strace -p 33917` + `lsof -p 33917` ile çalışan chancellor süreci analiz edildi ✅

### Bulgular (23 Mayıs 2026)

| Dosya / Yol | Erişim Tipi | Not |
|-------------|-------------|-----|
| `/mnt/c/Kuroshin/logs/chancellor.log` | WRITE | Rotating log |
| `/root/kuroshin/memory/chroma/` | READ/WRITE | ChromaDB native Linux FS |
| `/root/kuroshin/venv/` | mem-mapped | Python venv |
| `/mnt/c/Kuroshin/` | cwd | Çalışma dizini |

**İki path namespace (doğal ve beklenen):**
- `/mnt/c/Kuroshin/` → script/config/log dosyaları (Windows FS)
- `/root/kuroshin/` → venv + ChromaDB data (native Linux FS — performans için doğru)

**Bulunan Bug — `C:\\Kuroshin\\scripts` (DÜZELTİLDİ ✅):**
- `kuroshin_chancellor.py` satır 3213 + 3439: WSL Python içinde Windows path kullanılıyordu
- `/chat /scout_esik list` ve `/onay /red /kota` komutları bu satırdan geçiyor
- Düzeltme: `C:\\Kuroshin\\scripts` → `/mnt/c/Kuroshin/scripts`

---

## 1. İsimlendirme Evrimi (ASKIDA — Uygulanmayacak)

> Bu plan tarihsel kayıt olarak korunuyor. Uygulanmayacak.

| Mevcut (Korunacak) | Önerilen Yeni Ad | Neden İptal |
| :--- | :--- | :--- |
| `OTONOM_AJAN_PROTOKOLU.md` | `AUTONOMOUS_AGENT_PROTOCOL.md` | 20+ shell/py referansı kırılır |
| `KUROSHIN_MASTER_ROADMAP.md` | `MASTER_ROADMAP.md` | Bat, py, md çapraz referans |
| `YAPILACAK_GOREVLER.md` | `TASKS.md` | Chancellor araçları bu adı hardcode ediyor |
| `agents/kuroshin_chancellor.py` | `src/agents/chancellor/chancellor.py` | Tüm start scriptleri kırılır |
| `scripts/kuroshin_security.py` | `src/core/security/security.py` | 8+ Python import kırılır |
| `memory/active_model.json` | `data/state/active_model.json` | 8 servis bu yolu hardcode ediyor |

---

## 2. Kritik Tamir Matrisi (Referans — Rename yapılırsa)

> Yeniden adlandırma yapılmayacağından bu matris şu an geçersiz. İleride rename kararı alınırsa buraya bakılacak.

- **MCP Config:** `.mcp.wsl.json` araç yolları
- **Bat PowerShell:** `active_model.json` yolu
- **Imports:** Python `sys.path.insert` satırları
- **Test Suites:** `iron_inquisitor/*.json` mutlak yollar

---

## 3. Güvenlik ve Doğrulama Protokolü (Geçerli)

Rename yerine, mevcut sistem üzerinde path doğrulama:

1. `Iron Inquisitor --skip-passed` ile mevcut test durumunu teyit et
2. Herhangi bir değişiklik öncesi Iron Inquisitor tam suite çalıştır
3. Değişiklik sonrası tekrar çalıştır — PASS sayısı düşmemeli

---

## 4. Tamamlanan Çalışmalar

- [x] **Adım 0:** Spy araçları yazıldı (`kuroshin_spy.py`, `wsl_spy.sh`) — 22 Mayıs 2026
- [x] **Adım 1:** `lsof -p 33917` + `strace -p 33917` ile canlı analiz yapıldı — 23 Mayıs 2026
- [x] **Adım 2:** Log analizi — `/mnt/c` ve `/root/kuroshin` iki namespace beklenen ve doğru
- [x] **Adım 3:** `C:\\Kuroshin\\scripts` Windows path bug'ı düzeltildi (chancellor.py satır 3213+3439) — Iron Inquisitor 14/14 %100 PASS
- [x] **Adım 4 (YÖN DEĞİŞİKLİĞİ):** Rename planı iptal → AJAN-10 token bütçe + semantik dedup'a geçildi

---

## Sonuç

Bu dosya görevi tamamladı. Buradan çıkan tek somut değişiklik:
- `chancellor.py` satır 3213+3439: `C:\\Kuroshin\\scripts` → `/mnt/c/Kuroshin/scripts` ✅

Yapı optimizasyonu bu oturumda yapılmayacak. Sonraki iş: **AJAN-10**.

(23 Mayıs 2026 — KAPANDI)
