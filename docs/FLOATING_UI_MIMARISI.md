# Kuroshin Floating UI — Mimari & Tasarım Belgesi
**Versiyon:** v0.4 — Teknoloji + Entegrasyon + 3 Mod Kesinleşti  
**Tarih:** 12 Haziran 2026  
**Durum:** 🟠 FAZ-1 BAŞLIYOR — Stitch çıktısı onaylandı, kod yazılacak  

---

## 1. VİZYON

Kuroshin'in otonom zekasını masaüstüne **görünür kılan** katman.  
Telegram'daki Chancellor ile konuşabiliyorsun — şimdi aynı konuşma,  
masaüstünde cam efektli, minimal, her zaman üstte duran bir pencerede de olacak.

**İlham:** Omi (macOS floating bar) + Pluely (şeffaf cam overlay)  
**Fark:** Kuroshin'e özgü — canlı sıvı orb, Chancellor yanıtları, ajan durumu, fiyat alarmları

**Stitch AI Çıktısı (12 Haz 2026):** `C:\Kuroshin\kuroshin-downloads\stitch_kuroshin_floating_desktop_widget`  
→ `kuroshin_system/DESIGN.md` — onaylı stil rehberi (doğrudan kullanılır)  
→ `project_circle_.../code.html` — orb WebGL shader'ı (entegre edilecek)

---

## 2. TASARIM SİSTEMİ (Stitch AI — Onaylı)

Kaynak: `kuroshin_system/DESIGN.md`

### 2.1 Renk Paleti

```
Surface (zemin):     #131313
Surface bright:      #393939
On-surface (metin):  #E5E2E1
On-surface variant:  #C4C7C8
Outline:             #8E9192
Outline variant:     #444748
Primary (vurgu):     #FFFFFF
Primary container:   #E2E2E2
Background:          #131313
```

Etkileşim durumları **opacity shift** ile yapılır (renk değişmez):
- Aktif: %100 white
- Hover: %70 white  
- Disabled: %40 white

### 2.2 Tipografi

**Tek font: JetBrains Mono** (tüm boyutlarda, tüm bileşenlerde)

```
headline-lg:  24px / 700 / -0.02em  ← başlıklar
headline-md:  20px / 600 / -0.01em
headline-sm:  16px / 600
body-lg:      14px / 400            ← mesaj metni
body-md:      13px / 400
label-lg:     12px / 600            ← LED etiketleri, status
label-sm:     10px / 500
mono-code:    12px / 400            ← komut satırı
```

### 2.3 Spacing (4px grid kuralı)

```
xs:     4px
sm:     8px
md:     16px
lg:     24px
xl:     32px
gutter: 12px
```

Tüm padding/margin değerleri 4'ün katı olacak.

### 2.4 Yüzey Katmanları (Derinlik)

```
Katman 0 — OS wallpaper / #000000
Katman 1 — Mica Surface: #1A1A1A %80 opacity + backdrop-blur 30px
Katman 2 — Widget/Card: #FFFFFF %5 opacity + 1px white %20 border
Katman 3 — Floating menus: #1A1A1A %95 + shadow 0 8px 32px rgba(0,0,0,0.4)
```

### 2.5 Şekil & Köşe

```
Container (kart, widget, panel): 16px border-radius
Butonlar, input alanları:         8px border-radius
Chip/etiket:                      4px border-radius
Orb:                              tam daire (9999px)
```

---

## 3. KULLANICI DENEYİMİ — ONAYLANMIŞ AKIŞ

### 3.1 İki Durum

```
DURUM 1: DARALTILMIŞ (varsayılan)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4 köşeden birinde küçük canlı orb yüzüyor (sürüklenebilir, snap).
Etiket yok — sadece saf WebGL sıvı küre.
Fare ya da tuş olmadan kendi kendine nefes alıyor.
Masaüstü tamamen görünür, orb engel değil.

DURUM 2: GENİŞLEMİŞ (tıklayınca)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Orba tıklanınca panel orb'dan BÜYÜYEREK çıkar (expand, 300ms).
Orb yerinde KALIYOR, panel onun iç tarafında durur.
Sohbet geçmişi scroll edilebilir — tüm mesajlar kayıtlı.
Tekrar tıklayınca veya ✕ ile panel kapanır, orb yalnız kalır.
```

### 3.2 Kesinleşen Tasarım Kararları (Soru-Cevap — 12 Haz)

```
KARAR                     SEÇİM
──────────────────────────────────────────────────────────────────
Orb açma yöntemi          Tıklayınca aç/kapat
Açılma animasyonu         Expand — panel orb'dan büyür çıkar (300ms)
Orb kapanma/panel açık    Orb sağda kalır, panel solunda durur
Orb pozisyon              Sürüklenebilir → bırakınca en yakın köşeye snap
Düşünme animasyonu        Hızlanır + turkuaz (#00E6D9) parlar
Yanıt gelince             Beyaz flash 200ms → tekrar idle
Fiyat alarm               Orb sarı titrer 3x + Windows tray balonu (panel açılmaz)
Orb etiketi (daralt.)     Hiçbir şey — sadece saf orb, sade
Sohbet geçmişi            Kaydırılabilir tam geçmiş (scrollable)
Scroll çubuğu             4px, #9E9E9E, track yok (Stitch tasarım sistemi)
──────────────────────────────────────────────────────────────────
Context-aware             AÇIK — herhangi uygulamada metin seç →
                          orb titrer → tıkla → popup (Kopyala /
                          Kuroshin'e gönder / Özetle)
Auto-hide                 2 dk kullanılmazsa 64px → 32px küçülür
                          Hover/tıklayınca tekrar 64px'e büyür
Cam efekti                Liquid Glass — iOS/macOS 26 Tahoe tarzı
                          Su damlası/balon hissi: tam şeffaf arka plan,
                          refraction + reflection, sadece blur değil.
                          Masaüstünde ekranda bir su balonu varmış gibi.
Panel genişliği           320px sabit
Input davranışı           Tek satır — Enter = gönder, Shift+Enter = ↵
──────────────────────────────────────────────────────────────────
Sistem butonları          Phosphor Icons (SVG, 6 kalınlık, Apple/SF tarzı)
                          RAM bar + Purge + Chancellor restart +
                          LLM aç/kapat + Balon kapat
İkon sistemi              Phosphor Icons — MIT, SVG, PyQt6'ya direkt
Mikrofon göstergesi       Ses yüksekliğine göre dalga genişler/daralır
                          waveform rengi + hızı ses ritmini yansıtır
LLM modu                  2 mod: Hafif (test bekliyor) + Tam (35B)
                          FAZ-1'de LLM'siz, model sonra eklenir
Telegram sync             Çift yönlü: Telegram → Balon, Balon → Telegram
Hotkey                    YOK — sadece orba tıkla
Chancellor DOWN           Ghost mod: shader yavaşlar, %30 opacity
Idle nefes ritmi          4 saniye döngü — yavaş, sakin, dikkat çekmez
──────────────────────────────────────────────────────────────────
Panel kapatma             3 yol: ✕ butonu + orba toggle + click-outside
Zaman damgası             Hover'da görünür — fare gelince, çekilince kayar
Input placeholder         BOŞ — sadece cursor bekler ( | )
Panel başlığı             YOK — direkt durum şeridi: CH● LM● WK● RAM ✕
Sesli komut               Ses yüksekliğine göre waveform genişler/daralır
                          renk + hız ses ritmini yansıtır
──────────────────────────────────────────────────────────────────
Panel yüksekliği          DİNAMİK — içeriğe göre akıllı resize
                          min: 300px, max: 680px, spring animation
                          asla donma/kasma yok, smooth geçiş
İlk bağlanma mesajı       Chancellor _selamlama() — vakit bazlı
                          (Günaydın/İyi akşamlar + VRAM + mood)
                          typewriter ile yazılır
Akıllı scroll             Alttaysan: otomatik aşağı
                          Yukarı scrollluyorsan: "↓ N yeni" butonu
Orb hover                 Scale 1.1x + hafif parlama, 150ms ease-out
Sistem butonları konumu   Alt şerit (sohbet + input'un altında)
Waveform rengi            Ses yüksekliğine göre: beyaz → turkuaz → beyaz flash
                          + Chancellor MOOD'una göre ana renk:
                            merak      → #00BCD4 (cyan)
                            heyecan    → #FF6B35 (turuncu)
                            sogukkan   → #E0E0E0 (soğuk beyaz)
                            gurur      → #FFD700 (altın)
                            yorgunluk  → #7B68EE (lavanta)
                            huzun      → #4169E1 (koyu mavi)
                            ofke       → #FF4444 (kırmızı)
                            derin_d.   → #9B59B6 (mor)
                            bagli_h.   → #E91E63 (pembe)
                            nötr       → #FFFFFF (beyaz)
Mini orb (32px, 2dk)      Shader kapanır — pulse nokta (4sn nabız)
                          32px → 36px → 32px, scale only, tıklanabilir
```

### 3.3 Layout Diyagramı

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                     MASAÜSTÜ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 [daraltılmış — 4 köşeden biri, örnek sağ alt]

                                             ╭────╮
                                             │ 🌊 │  ← saf orb, etiket yok
                                             ╰────╯

 [genişlemiş — panel orb'dan büyüyerek çıktı]

                              ╭──────────────╮ ╭────╮
                              │ ▣ Kuroshin ✕ │ │    │
                              │ ──────────── │ │ 🌊 │
                              │ CH● LM● WK●  │ │    │
                              │              │ ╰────╯
                              │ 🤖 msg 1   ▲ │
                              │ 👤 msg 2   │ │  ← scrollable
                              │ 🤖 msg 3   │ │
                              │            ▼ │
                              │ [komut..] [▶]│
                              ╰──────────────╯

 Snap pozisyonları:
   Sağ alt (varsayılan) → panel sola açılır, yukarı büyür
   Sol alt              → panel sağa açılır, yukarı büyür
   Sağ üst              → panel sola açılır, aşağı büyür
   Sol üst              → panel sağa açılır, aşağı büyür
```

### 3.4 Tıklama Akışı

```
LORD MASAÜSTÜNDE ÇALIŞİYOR
        │
        ▼
  Sağ altta orb yavaşça nefes alıyor
  [sakin animasyon — dikkat çekmiyor]
        │
  Lord orba tıklar
        │
        ▼
  Panel sol yandan kayarak açılır (300ms ease)
  Orb yerinde kalır, küçülmez
        │
  Lord mesaj yazar → [▶] veya Enter
        │
        ▼
  Orb HIZLANIR + turkuaz parlar [Chancellor işliyor]
  Panelde akan yazı başlar
        │
        ▼
  Yanıt tamamlanır
  Orb yavaşlar, normale döner
        │
  Esc veya ✕ ile panel kapanır
  Orb yeniden tek başına köşede
```

---

## 4. ORB TASARIMI & ANİMASYON DURUMLARI

### 4.1 Orb Boyutu ve Pozisyonu

```
Boyut:     64×64px (daraltılmış), 48×48px (panel açıkken — biraz küçülür)
Pozisyon:  Sağ alt köşe, 24px margin
Z-index:   En üst (always-on-top)
```

### 4.2 WebGL Shader Özellikleri (Project Circle'dan)

Orb'un iç dokusu canlı WebGL shader ile üretilir:
- 8 adet fluid/metaball blob sürekli hareket eder
- fBm (fractal brownian motion) ile organik deformasyon
- Fare yaklaşınca orb elastik olarak uzanır (yapışkan fizik)
- Rim light + specular highlight → gerçekçi cam/sıvı görünümü

### 4.3 Animasyon Durumları

```
┌─────────────────────────────────────────────────────────────────┐
│  DURUM         │ Shader hızı │ Renk              │ Kenar         │
├─────────────────────────────────────────────────────────────────┤
│  IDLE          │  0.2x       │ Koyu lacivert/mor │ 1px %20 white │
│  (bekliyor)    │  yavaş nefes│ #010410 → #721090 │ sakin         │
├─────────────────────────────────────────────────────────────────┤
│  PROCESSING    │  1.5x       │ Turkuaz parlıyor  │ pulse glow    │
│  (Chancellor   │  hızlı akış │ #00E6D9 dominant  │ #00E6D9 %60   │
│   düşünüyor)   │             │                   │               │
├─────────────────────────────────────────────────────────────────┤
│  DONE          │  0.4x       │ Beyaz flash (200ms)│ %80 white     │
│  (yanıt geldi) │  sonra idle │ sonra idle'a döner│ sonra normal  │
├─────────────────────────────────────────────────────────────────┤
│  ALARM         │  1.0x       │ Sarı/turuncu      │ titreme 3x    │
│  (fiyat alarmı)│             │ #FFB300 flash     │ 5px yatay     │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 Fiyat Alarm Davranışı

```
PriceWatcher → alarm tetiklendi
        │
        ├── Orb: sarı/turuncu flash + 3x yatay titreme
        │
        └── Windows tray bildirimi:
            ┌─────────────────────────┐
            │ 🔔 Kuroshin             │
            │ Ford Focus: -4.8%       │
            │ 145.000₺ → 138.000₺     │
            └─────────────────────────┘
            [sağ alt köşe, 5 sn görünür]

Panel OTOMATIK AÇILMAZ — Lord görmek isteyince orba tıklar.
```

---

## 5. SOHBET PANELİ TASARIMI

### 5.1 Panel Anatomisi

```
╭──────────────────────────────────────────╮
│ ▣  Kuroshin              ─  □  ✕        │  ← başlık — sürükle
├──────────────────────────────────────────┤
│  ● CH  ● LM  ● WK       CPU:48° GPU:63° │  ← status_bar
├──────────────────────────────────────────┤
│                                          │
│  [12 Haz 15:32]                          │
│  ╭────────────────────────────────────╮  │
│  │ 🤖  Hazır. Ne araştıralım?         │  │  ← bot mesajı
│  ╰────────────────────────────────────╯  │
│                                          │
│  ╭────────────────────────────────────╮  │
│  │ 👤  bisiklet ara bütçem 3000       │  │  ← kullanıcı mesajı
│  ╰────────────────────────────────────╯  │
│                                          │
│  ╭────────────────────────────────────╮  │
│  │ 🤖  🔍 Epey taranıyor...           │  │  ← akan yazı
│  │     ▰▰▰▰▰▱▱▱▱▱  50%              │  │  ← progress bar
│  ╰────────────────────────────────────╯  │
│                                          │
├──────────────────────────────────────────┤
│  [ Mesajınızı yazın...          ] [▶]   │  ← input
╰──────────────────────────────────────────╯

Boyut: 320×480px
Pozisyon: Orb'un solunda, aynı alt hizasında
Arka plan: Mica blur (#131313 %80 + backdrop-blur 30px)
```

### 5.2 Mesaj Balonları

```
Bot mesajı:
  Zemin: #FFFFFF %5 opacity
  Kenarlık: 1px #FFFFFF %20
  Padding: 12px
  Font: JetBrains Mono 13px

Kullanıcı mesajı:
  Zemin: #FFFFFF %10 opacity (biraz daha parlak)
  Kenarlık: 1px #FFFFFF %30
  Padding: 12px
  Font: JetBrains Mono 13px

Akan yazı imleci: 8×16px beyaz dikdörtgen, 1s blink
Progress bar: 2px tam genişlik, #00E6D9, left-to-right fill
```

---

## 6. MİMARİ GENEL BAKIŞ

### 6.1 Sistem Topolojisi

```
┌───────────────────────────────────────────────────────────────┐
│                   WINDOWS 11 (Lord masaüstü)                  │
│                                                               │
│  ┌──────────────────┐    ┌──────────────────────────────────┐ │
│  │  FloatingUI      │    │  Bridge (bridge.py)              │ │
│  │  (pywebview)     │◄──►│  Windows Python                  │ │
│  │  ┌────────────┐  │    │  • WebSocket hub (:9003)         │ │
│  │  │ Orb WebGL  │  │    │  • Telegram getUpdates poll      │ │
│  │  │ Chat panel │  │    │  • alarm.py alert alır           │ │
│  │  │ Sistem btn │  │    │  • Chancellor HTTP poll (:9005)  │ │
│  │  └────────────┘  │    └──────────────┬───────────────────┘ │
│  │  pystray tray    │                   │ ws://127.0.0.1:9005  │
│  └──────────────────┘                   │ (WSL2 localhost fwd) │
│                                         │                      │
│  ┌──────────────────────────────────────▼───────────────────┐ │
│  │  KuroRecon alarm.py (Windows Python)                     │ │
│  │  Fiyat alarm tetiklenir → WebSocket bridge'e alert JSON  │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬─────────────────────────────┘
                                  │ WSL2 localhost forwarding
┌─────────────────────────────────▼─────────────────────────────┐
│  WSL2 Ubuntu-22.04 (Kuroshin Core)                            │
│                                                               │
│  ┌─────────────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ Chancellor          │  │ Llama-server│  │ Walker :9002 │  │
│  │ + aiohttp :9005     │  │ :8080       │  │              │  │
│  │   GET /status       │  │ GET /health │  │ GET /health  │  │
│  │   POST /message     │  └─────────────┘  └──────────────┘  │
│  │   SSE /stream       │                                      │
│  └─────────────────────┘                                      │
└───────────────────────────────────────────────────────────────┘
```

### 6.2 3 Çalışma Modu

```
MOD 1: LITE (PC her açıldığında otomatik)
─────────────────────────────────────────────────────────
WSL kapalı ← FloatingUI + Bridge Windows'ta başlar
Orb: ghost mod (%30 opacity, yavaş shader)
CH●=KIRMIZI  LM●=KIRMIZI  WK●=KIRMIZI
Fiyat alarm monitörü aktif (KuroRecon Windows Python)
Windows Startup klasöründen otomatik başlar

MOD 2: KÜÇÜK LLM (askıda — Lord belirleyecek)
─────────────────────────────────────────────────────────
[LLM] toggle butonu → eklenir

MOD 3: FULL POWER ⚡ (bat [1] simülatörü)
─────────────────────────────────────────────────────────
[⚡ Full Power] butonuna basılır
Python subprocess WSL komutlarını sırayla çalıştırır:
  1. Llama-server başlar (240s) → LM● yeşile döner
  2. Chancellor başlar       → CH● yeşile döner
  3. Walker başlar           → WK● yeşile döner
Terminal gerektirmez. Status LED'ler birer birer yanar.
```

---

## 7. DOSYA YAPISI (Hedef)

```
C:\Kuroshin\
├── kuroshin_floating_ui/
│   ├── main.py                    ← pythonw ile başlatılır
│   │                                 pywebview window + pystray + watchdog
│   ├── bridge.py                  ← Windows Python WebSocket hub (:9003)
│   │                                 Telegram poll + Chancellor HTTP poll
│   │                                 alarm.py alert alır → UI'ya iletir
│   ├── api.py                     ← JS'den çağrılan Python API sınıfı
│   │                                 move_window, send_message, get_status
│   │                                 full_power_start, chancellor_restart
│   ├── modes.py                   ← Mod yöneticisi (LITE/LLM/FULL)
│   │                                 WSL subprocess komutları
│   ├── requirements.txt           ← pywebview, pystray, websockets, pillow
│   ├── settings.json              ← pozisyon, son mod, opacity
│   ├── web/
│   │   ├── index.html             ← UI kök (pywebview file:// açar)
│   │   ├── orb.js                 ← WebGL shader (stitch'ten direkt)
│   │   ├── chat.js                ← Sohbet + mesaj render + typewriter
│   │   ├── system.js              ← Status LED, sistem butonları
│   │   ├── animations.js          ← fade, shake, snap, auto-hide
│   │   └── style.css              ← Liquid Glass, JetBrains Mono, tüm stiller
│   └── assets/
│       └── icon.ico
│
├── scripts/
│   └── chancellor_http_server.py  ← Chancellor'a entegre aiohttp mini server
│                                     WSL :9005 — GET /status, POST /message, SSE /stream
│                                     (chancellor.py import eder, ortak venv)
│
└── kuroshin-downloads/
    └── stitch_kuroshin_floating_desktop_widget/
        ├── kuroshin_system/DESIGN.md        ← STİL REHBERİ (onaylı)
        └── project_circle_.../code.html     ← ORB SHADER KAYNAĞI
```

---

## 8. TEKNOLOJİ YIĞINI

```
Katman            Teknoloji                  Neden
─────────────────────────────────────────────────────────
UI Framework      pywebview                  WebGL+CSS direkt, hafif
                                             Win11 WebView2 (Edge) = zaten kurulu
Orb render        WebGL (canvas)             Stitch shader hiç değişmeden çalışır
Cam efekti        CSS backdrop-filter        Liquid Glass native, blur+refraction
System tray       pystray + pillow           bağımlılıksız, Win11 uyumlu
WebSocket hub     bridge.py (Windows Py)     Tek merkez: UI↔Chan↔alarm
Chancellor IPC    aiohttp :9005 (WSL)        GET /status, POST /message, SSE /stream
Mesaj format      marked.js (client-side)    Telegram markdown → HTML, ASCII korunur
WSL subprocess    Python subprocess+wsl      Full Power terminalsiz başlatma
Win Startup       shell:startup kısayol      Lite mod PC açıkken otomatik

Değerlendirilen ama seçilmeyenler:
✗ PyQt6          : Shader'ı GLSL'e çevirmek gerekiyor, karmaşık
✗ Electron/Tauri : Node.js / Rust bağımlılığı
✗ Unity          : C#, overkill, Kuroshin entegrasyonu zor
✗ Tkinter        : Liquid Glass / WebGL efekti yok
```

---

## 9. IPC PROTOKOLÜ

### 9.1 Bridge (:9003) ↔ FloatingUI (pywebview JS evaluate)

Bridge, Windows Python → JS `window.dispatchEvent(new CustomEvent(...))` ile iletişim:

```json
{"type": "stream",  "chunk": "🔍 Epey taranıyor...", "session_id": "abc", "ts": 0}
{"type": "done",    "text": "🏆 Sonuç...",           "session_id": "abc", "ts": 0}
{"type": "status",  "chancellor": "UP", "llama": "UP", "walker": "UP",
                    "llama_vram_gb": 5.2, "cpu_temp": 48, "gpu_temp": 63, "ts": 0}
{"type": "alert",   "category": "price_alarm", "title": "Ford Focus fiyat düştü!",
                    "body": "145.000₺ → 138.000₺ (-4.8%)", "ts": 0}
{"type": "notify",  "level": "info", "text": "Cookie 7 gün içinde sona eriyor!", "ts": 0}
{"type": "telegram","text": "Lord'dan Telegram mesajı", "direction": "incoming", "ts": 0}
```

FloatingUI → Bridge (pywebview expose API → Python):

```python
api.send_message("bisiklet ara bütçem 3000")   # → Chancellor'a POST
api.full_power_start()                          # → WSL subprocess zinciri
api.chancellor_restart()                        # → WSL restart_chancellor.sh
api.get_status()                                # → /status poll tetikle
api.move_window(x, y)                          # → pywebview window.move()
```

### 9.2 Bridge ↔ Chancellor (WSL :9005 aiohttp)

```
GET  /status   → {"chancellor":"UP","llama":"UP","walker":"UP","vram":5.2,"ts":0}
POST /message  → {"text":"bisiklet ara bütçem 3000","session_id":"abc"}
SSE  /stream   → data: {"type":"chunk","text":"🔍 Epey taranıyor..."}\n\n
```

Bridge 10sn'de bir `GET /status` poll eder. Chancellor mesajları `SSE /stream` üzerinden push eder.
send_msg hook: chancellor.py'de her `send_msg()` çağrısı SSE client'larına da gönderir.

### 9.3 alarm.py → Bridge

```json
{"type": "price_alert", "product": "Ford Focus", "old": 145000,
 "new": 138000, "pct": -4.8, "ts": 0}
```

alarm.py → `ws://127.0.0.1:9003/alert` (Bridge WebSocket endpoint)

### 9.4 Telegram → Bridge (getUpdates poll)

Bridge 2sn'de bir Bot API getUpdates çağırır. Gelen mesajlar `{"type":"telegram"}` olarak UI'ya iletilir.
Giden mesajlar (UI → Chancellor) Telegram'a da kopyalanır (sendMessage).

### 9.5 Status LED güncelleme sıklığı

```
CH●  ← /status GET 10sn aralık (WSL :9005)
LM●  ← /health GET 10sn aralık (WSL :8080)
WK●  ← /health GET 10sn aralık (WSL :9002)
Kırmızı: bağlantı hatası veya timeout
```

---

## 10. BAT ENTEGRASYONU

### Başlatma ([1] Walker Modu)

```batch
:: [6/6] FloatingUI + Bridge başlat (ikisi de Windows Python, WSL gerektirmez)
echo [6/6] FloatingUI baslatiliyor...
start "Kuroshin FloatingUI" /B pythonw "C:\Kuroshin\kuroshin_floating_ui\main.py"
:: Bridge main.py içinden thread olarak başlar (ayrı process değil)
timeout /t 2 /nobreak >nul
```

### Kapatma ([5] Purge)

```batch
:: FloatingUI watchdog process'ini kapat (bridge de biter)
taskkill /F /IM pythonw.exe 2>nul
:: WSL'deki Chancellor HTTP server (Full Power açıksa)
wsl -d Ubuntu-22.04 -- bash -c "pkill -f chancellor_http_server.py 2>/dev/null"
```

### Windows Startup (Otomatik Lite mod)

```
shell:startup → C:\Kuroshin\kuroshin_floating_ui\FloatingUI.lnk
Target: pythonw "C:\Kuroshin\kuroshin_floating_ui\main.py" --mode lite
```

### Full Power — Python subprocess komutları (ui/modes.py)

```python
# Llama başlat
subprocess.Popen(['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
    'setsid bash /mnt/c/Kuroshin/scripts/start_llama.sh < /dev/null &'])
# Chancellor başlat
subprocess.Popen(['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
    'setsid bash /mnt/c/Kuroshin/scripts/restart_chancellor.sh < /dev/null &'])
# Walker başlat
subprocess.Popen(['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
    'setsid bash /mnt/c/Kuroshin/scripts/start_walker.sh < /dev/null &'])
```

---

## 11. GELİŞTİRME FAZLARI

```
FAZ-1: Temel Pencere + Orb (1-2 sohbet) ← ŞU AN
────────────────────────────────────────────────────────
Temel kaynak: kuroshin-downloads/.../kuroshin_assistant_main_view/code.html (Stitch, onaylandı ✅)
□ kuroshin_floating_ui/ dizin yapısı (web/, assets/, ...)
□ pywebview frameless + transparent + always-on-top pencere
□ WebGL orb (stitch shader → web/orb.js direkt)
□ Orb animasyon durumları: IDLE / PROCESSING / DONE / ALARM
□ Sürüklenebilir orb + 4 köşe snap (JS)
□ Tıklayınca panel expand (300ms) + ✕ / click-outside kapat
□ pystray system tray (Göster/Gizle/Kapat)
□ settings.json pozisyon kalıcı (son nerede bırakıldıysa)
□ Watchdog: main.py subprocess restart
□ Bat [1] ile başlatma + bat [5] ile kapatma testi
□ Windows Startup kısayolu oluştur

Çıktı: Gerçek canlı orb + panel açılıp kapanıyor, bat + startup entegre

FAZ-2: Bridge + IPC (1 sohbet)
────────────────────────────────────────────────────────
□ bridge.py Windows Python WebSocket hub (:9003)
□ Chancellor aiohttp mini server (:9005) — /status + /message + SSE /stream
□ chancellor.py send_msg hook → SSE /stream push
□ Status LED'leri gerçek zamanlı (10sn poll)
□ Telegram getUpdates → UI'da görünür (çift yönlü)
□ alarm.py → bridge alert JSON → orb sarı shake + tray balonu

FAZ-3: Tam İnteraktif (1-2 sohbet)
────────────────────────────────────────────────────────
□ Input → Chancellor → akan yazı yanıt (SSE stream)
□ Processing sırasında orb hızlanıp turkuaz parlıyor
□ marked.js ile Telegram markdown → HTML render (ASCII korunur)
□ Full Power ⚡ butonu → WSL subprocess → LED'ler yeşile döner
□ Chancellor restart butonu → WSL restart script
□ Fiyat alarm listesi: alarm_config.yaml okunur, panelde gösterilir
□ Typewriter + auto-hide (2dk → 32px pulse)

FAZ-4: Gelişmiş (isteğe bağlı)
────────────────────────────────────────────────────────
? Context-aware: SetWinEventHook metin seç → orb titrer → popup
? Mod 2 küçük LLM (Lord belirleyecek)
? Ses bildirimi (playsound)
? Mikrofon input → Chancellor
? Click-through modu (WS_EX_TRANSPARENT)
```

---

## 12. RİSKLER & ÇÖZÜMLER

```
Risk                         Olasılık  Çözüm
──────────────────────────────────────────────────────────────────
pywebview transparent +      ORTA      backdrop-filter CSS fallback;
Liquid Glass Win10'da yok              Win11 test öncelikli
──────────────────────────────────────────────────────────────────
WSL2 :9005 → Windows         DÜŞÜK     Walker :9002 zaten bu yöntemle
localhost forwarding                   çalışıyor → kanıtlanmış pattern
──────────────────────────────────────────────────────────────────
Chancellor HTTP server        ORTA      Iron Inquisitor ile test;
ekleme chancellor.py bozar             yeni dosya chancellor_http_server.py
                                       import eder, izole
──────────────────────────────────────────────────────────────────
WSL subprocess Full Power    ORTA      Her adım status LED ile doğrulanır;
başlatma başarısız                     timeout 300s → hata bildirimi
──────────────────────────────────────────────────────────────────
pywebview + pystray           DÜŞÜK     Her ikisi Windows Python;
thread çakışması                       pystray ayrı thread, pywebview
                                       main thread zorunlu
──────────────────────────────────────────────────────────────────
WebGL shader perf (32px      DÜŞÜK     Auto-hide 2dk: shader kapanır,
sürekli render)                        CSS pulse animasyonu devralır
```

---

## 13. BAŞARI KRİTERLERİ

```
FAZ-1 bitti sayılır:
  □ pythonw main.py ile orb sağ alt köşede başlıyor
  □ WebGL shader canlı nefes alıyor (IDLE animasyon)
  □ Tıklayınca panel expand animasyonu ile açılıyor (300ms)
  □ Orb panelin sağında kalıyor, küçülmüyor
  □ Orb sürüklenebilir + bırakınca en yakın köşeye snap
  □ ✕ + orb toggle + click-outside → panel kapanıyor
  □ pystray ikonu var, sağ tık: Göster/Gizle/Kapat
  □ Taskbar'da görünmüyor (sadece tray)
  □ settings.json'a pozisyon kaydediliyor, yeniden açıkta aynı yer
  □ Watchdog: process ölünce yeniden başlar
  □ Bat [1] ve bat [5] çalışıyor
  □ PC açılışında otomatik başlıyor (shell:startup)

FAZ-2 bitti sayılır:
  □ Chancellor /status log'da görünüyor (10sn poll)
  □ CH●/LM●/WK● LED'leri gerçek durumu yansıtıyor
  □ Lord Telegram'dan yazıyor → FloatingUI'da da görünüyor
  □ alarm.py test → orb sarı shake + tray balonu çıkıyor

FAZ-3 bitti sayılır:
  □ FloatingUI'dan yazılan mesaj Chancellor'a gidiyor
  □ Chancellor yanıtı stream olarak panelde akan yazı ile çıkıyor
  □ Orb Chancellor düşünürken hızlanıp turkuaz parlıyor
  □ [⚡ Full Power] → LED'ler birer birer yeşile dönüyor
  □ Telegram markdown bold/code/ASCII tablolar düzgün render
```

---

## 14. REFERANSLAR

| Proje | Konum | Ne için |
|---|---|---|
| Stitch AI Design System | `kuroshin-downloads/.../kuroshin_system/DESIGN.md` | Onaylı stil rehberi |
| Orb WebGL Shader | `kuroshin-downloads/.../project_circle_.../code.html` | Orb animasyon kaynağı |
| pywebview | pypi.org/project/pywebview | Ana UI framework |
| pystray | pypi.org/project/pystray | System tray |
| marked.js | cdn.jsdelivr.net/npm/marked | Markdown → HTML |
| Pluely (ilham) | github.com/iamsrikanthnani/pluely | UX pattern |
| Omi macOS | macos.omi.me | Floating bar konsepti |

---

## 15. SORU-CEVAP KARAR TABLOSU (12 Haz 2026)

| Konu | Karar |
|---|---|
| UI Framework | pywebview + pystray |
| Bridge konumu | Windows Python (UI ile aynı process/thread) |
| Chancellor → UI stream | send_msg hook → SSE /stream push |
| Chancellor HTTP server | aiohttp :9005 (yeni dosya, chancellor.py import) |
| alarm.py → UI | Bridge WebSocket'e alert JSON |
| Context-aware | SetWinEventHook (FAZ-4) |
| Crash/restart | Watchdog subprocess restart |
| Status LED ölçüm | HTTP health check 10sn poll |
| Telegram → UI | getUpdates poll 2sn |
| Telegram → UI yönü | Çift yönlü |
| Başlatma sırası | FloatingUI önce, Bridge thread olarak, auto-reconnect |
| Windows Startup | shell:startup kısayol, Lite mod |
| Taskbar | Yok — sadece tray |
| Multi-monitor | settings.json son pozisyon |
| Mesaj format | marked.js client-side render |
| Input limit | Limit yok, dosya FAZ-4 |
| Full Power UX | [⚡ Full Power] tek tuş, LED birer birer yeşile |
| Mod 1 (Lite) | WSL yok, ghost mod, otomatik startup |
| Mod 2 | Askıda — Lord belirleyecek |
| Mod 3 (Full) | Tam bat [1]: Llama+Chancellor+Walker WSL subprocess |
| Sistem butonları | RAM purge, LLM toggle, Chancellor restart, Alarm listesi |

---

*Son güncelleme: 12 Haziran 2026 — v0.4 Teknoloji + Entegrasyon + 3 Mod kesinleşti*  
*Soru-cevap seansı 1: tıklayınca aç · hızlanıp parlar · panel yanında durur · tray bildirimi*  
*Soru-cevap seansı 2: pywebview seçildi · 3 mod · bridge Win · Chancellor HTTP · watchdog*
