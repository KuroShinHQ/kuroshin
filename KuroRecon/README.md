# Scraper Paketi — Web Scraping & Fiyat Takip Çözümü

**Versiyon:** 1.0.0  
**Gereksinimler:** Python 3.9+

Sahibinden, Hepsiburada, Trendyol ve diğer sitelerden otomatik veri toplama aracı.
Sonuçları CSV veya JSON olarak dışa aktarır.

---

## Hızlı Başlangıç

### 1. Kurulum

```bash
pip install -r requirements.txt
```

Playwright gerekiyorsa (Trendyol, Epey gibi JS-render siteler):
```bash
pip install playwright
playwright install chromium
```

### 2. Demo — Sahibinden Ford Focus

```bash
python demo_ford_focus.py
```

Cookie dosyasıyla:
```bash
python demo_ford_focus.py --cookies cookies.json --budget 300000
```

### 3. Tam Çalıştırma

`config.yaml` dosyasını düzenleyin, sonra:

```bash
python run.py
```

Konfigürasyon testi (gerçek istek atmadan):
```bash
python run.py --dry-run
```

---

## Konfigürasyon (config.yaml)

```yaml
sites:
  - name: "Sahibinden"
    url: "https://www.sahibinden.com/otomobil-ford-focus?pagingSize=50&sorting=price_asc"
    mode: "static"         # static | playwright
    parser: "sahibinden"   # sahibinden | trendyol | hepsiburada | epey | generic
    cookie_file: "cookies.json"
    enabled: true

output:
  format: "csv"            # csv | json
  file: "sonuclar.csv"
  sort_by: "price"
  ascending: true
  max_results: 50

scraper:
  delay_min: 3             # Saniye — çok düşük yapmayın (ban riski)
  delay_max: 8
  timeout: 30
  proxy: ""
```

---

## Cookie Dosyası Nasıl Hazırlanır?

Sahibinden gibi giriş gerektiren siteler için:

1. Chrome/Firefox'ta `cookies.json` eklentisi kurun  
   (EditThisCookie, Cookie-Editor vb.)
2. İlgili siteye hesabınızla giriş yapın
3. Eklentiden "Export as JSON" seçin
4. Dosyayı `cookies.json` adıyla bu klasöre kaydedin

---

## Desteklenen Site Türleri

| Parser        | Site                | Mod       | Not                          |
|---------------|---------------------|-----------|------------------------------|
| `sahibinden`  | sahibinden.com      | static    | Cookie gerektirir (2026)     |
| `trendyol`    | trendyol.com        | playwright| JS-render — Playwright şart  |
| `hepsiburada` | hepsiburada.com     | static    | Giriş gerekmez               |
| `epey`        | epey.com            | playwright| JS-render — Playwright şart  |
| `generic`     | Herhangi bir site   | static    | JSON-LD destekleyen siteler  |

---

## Docker ile Çalıştırma

```bash
# Image oluştur
docker build -t scraper-paket .

# Çalıştır (çıktı ./cikti klasörüne gelir)
docker run --rm \
  -v $(pwd)/cookies.json:/app/cookies.json \
  -v $(pwd)/cikti:/app/cikti \
  scraper-paket
```

---

## Proje Yapısı

```
scraper_paketi/
├── fetcher.py      — HTTP istemcisi (curl_cffi + anti-bot bypass)
├── parser.py       — HTML parser (JSON-LD + site-spesifik CSS)
└── exporter.py     — CSV/JSON çıktı + konsol tablosu

config.yaml         — Müşteri konfigürasyonu (tek düzenleme noktası)
run.py              — Ana çalıştırıcı
demo_ford_focus.py  — Sahibinden Ford Focus demo
requirements.txt    — Python bağımlılıkları
Dockerfile          — Docker konteynır
```

---

## Sorun Giderme

**"Engellendi / Bot koruması" hatası:**
- `delay_min`/`delay_max` değerlerini artırın (örn. 5/12)
- Cookie dosyası ekleyin
- Proxy kullanmayı deneyin

**Playwright yüklü değil:**
```bash
pip install playwright && playwright install chromium
```

**0 sonuç geldi:**
- URL'yi tarayıcıda açıp içerik geldiğini doğrulayın
- `parser` türünü `generic` olarak değiştirip deneyin
- Site HTML yapısı değişmiş olabilir — iletişime geçin

---

## Destek & Özelleştirme

Bu paket belirli bir müşteri ihtiyacına göre özelleştirilebilir:
- Yeni site parser'ları ekleme
- Otomatik zamanlama (cron/görev zamanlayıcı)
- E-posta/Telegram bildirim entegrasyonu
- Fiyat değişikliği alarmları
- Çoklu sayfa desteği (pagination)
