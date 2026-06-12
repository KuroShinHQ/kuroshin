# Kuroshin Floating UI — Mimari & Tasarım Belgesi
**Versiyon:** v0.1 — Mimari Taslak  
**Tarih:** 12 Haziran 2026  
**Durum:** 🔵 Araştırma tamamlandı — Geliştirme bekliyor  

---

## 1. VİZYON

Kuroshin'in otonom zekasını masaüstüne **görünür kılan** katman.  
Telegram'daki Chancellor ile konuşabiliyorsun — şimdi aynı konuşma,  
masaüstünde cam efektli, minimal, her zaman üstte duran bir pencerede de olacak.

**İlham:** Omi (macOS floating bar) + Pluely (şeffaf cam overlay)  
**Fark:** Kuroshin'e özgü — Chancellor yanıtları, ajan durumu, fiyat alarmları

---

## 2. KULLANICI DENEYİMİ (UX AKIŞI)

```
Lord bilgisayarı açar
        │
        ▼
  Kuroshin.bat → [1] Walker Modu
        │
        ├─► Chancellor başlar (Telegram bot)
        ├─► Llama-server başlar
        ├─► Walker başlar
        └─► [YENİ] FloatingUI başlar  ◄── bu proje
              │
              ▼
    ┌─────────────────────────────┐
    │  ●  Kuroshin               │  ← her zaman üstte
    │  ─────────────────────     │  ← cam/mica arka plan
    │  > Hazır. Komutunuz?       │  ← akan yazı
    │                            │
    │  [ Yaz... ]    [ 🎤 ]      │  ← input + mikrofon
    └─────────────────────────────┘
              │
              │  Lord mesaj yazar → Chancellor'a gider
              │  Chancellor yanıtlar → FloatingUI'a gelir
              ▼
    ┌─────────────────────────────┐
    │  ●  Kuroshin        ▐█▌ ~  │  ← işleme animasyonu
    │  ─────────────────────     │
    │  > Market araştırılıyor... │  ← stream
    │    ▰▰▰▰▰▱▱▱▱▱  48%        │  ← progress bar
    └─────────────────────────────┘
```

---

## 3. MİMARİ GENEL BAKIŞ

```
┌─────────────────────────────────────────────────────────────────┐
│                    KUROSHIN FLOATING UI                         │
│                    (Windows 11 Desktop)                         │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐         ┌──────────────────────────────┐
  │   LORD (Kullanıcı)│         │   KUROSHIN CORE (WSL2)       │
  │                  │         │                              │
  │  ┌────────────┐  │         │  ┌────────────────────────┐ │
  │  │ FloatingUI │  │◄──IPC──►│  │  Chancellor (Telegram) │ │
  │  │  (PyQt6)   │  │         │  │  + Llama-server        │ │
  │  └────────────┘  │         │  │  + Walker              │ │
  │        │         │         │  └────────────────────────┘ │
  │        │         │         │           │                  │
  │  ┌─────▼──────┐  │         │  ┌────────▼───────────────┐ │
  │  │  Telegram  │  │◄────────│  │  FloatingUI Bridge     │ │
  │  │  (mobil)   │  │         │  │  (HTTP/WebSocket :9003)│ │
  │  └────────────┘  │         │  └────────────────────────┘ │
  └──────────────────┘         └──────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │                   IPC PROTOKOLÜ                              │
  │                                                              │
  │  FloatingUI (Windows PyQt6)  ◄──► FloatingBridge (WSL2)     │
  │                                                              │
  │  Protokol: WebSocket (ws://127.0.0.1:9003)                   │
  │  Format  : JSON stream                                       │
  │  Auth    : BRIDGE_SECRET (.env)                              │
  └──────────────────────────────────────────────────────────────┘
```

---

## 4. BILEŞEN MİMARİSİ

### 4.1 FloatingUI (Windows Tarafı — PyQt6)

```
kuroshin_floating_ui/
├── main.py                    ← giriş noktası, bat'tan çağrılır
├── ui/
│   ├── floating_window.py     ← ana pencere (FramelessWindow + Mica)
│   ├── chat_widget.py         ← mesaj listesi (akan yazı animasyonu)
│   ├── input_widget.py        ← metin kutusu + gönder butonu
│   ├── status_bar.py          ← ajan durumu (Chancellor/Walker/Llama)
│   └── tray_icon.py           ← system tray (sağ tık menü)
├── core/
│   ├── bridge_client.py       ← WebSocket bağlantı yöneticisi
│   ├── message_model.py       ← mesaj veri modeli
│   └── settings.py            ← pencere pozisyon, opacity, tema
├── effects/
│   ├── mica_effect.py         ← Windows 11 Mica efekti (win32mica)
│   ├── acrylic_effect.py      ← Windows 10 Acrylic fallback
│   └── animations.py          ← akan yazı, fade-in, pulse
└── assets/
    ├── icon.png               ← Kuroshin ikonu
    └── sounds/
        └── notify.wav         ← bildirim sesi (opsiyonel)
```

### 4.2 FloatingUI Bridge (WSL2 Tarafı — Python)

```
scripts/
└── kuroshin_floating_bridge.py   ← WebSocket sunucu (:9003)
    │
    ├── Chancellor hook           ← chancellor mesaj gönderince bridge'e iletir
    ├── Sistem durumu yayını      ← her 5s Llama/Walker/Chancellor durumu
    └── İki yönlü iletişim       ← UI'dan gelen mesajı Chancellor'a iletir
```

---

## 5. VERİ AKIŞI DİYAGRAMLARI

### 5.1 Lord → FloatingUI → Chancellor Akışı

```
Lord, FloatingUI'a yazar: "bisiklet ara bütçem 3000"
        │
        ▼
  [FloatingUI — input_widget.py]
  Metin alındı → WebSocket üzerinden bridge'e gönder
        │
        ▼ ws://127.0.0.1:9003
  {"type": "user_message", "text": "bisiklet ara bütçem 3000", "ts": 1718...}
        │
        ▼
  [FloatingBridge — kuroshin_floating_bridge.py]
  Mesajı Chancellor'ın iç API'sine ilet (POST /inject veya mevcut tool sistemi)
        │
        ▼
  [Chancellor — kuroshin_chancellor.py]
  market_master_query() tetiklenir → stream başlar
        │
        ▼ (stream olayları)
  {"type": "stream", "chunk": "🔍 Epey taranıyor..."}
  {"type": "stream", "chunk": "▰▰▰▱▱▱ 40%"}
  {"type": "done",   "text": "🏆 Sonuç: Triathlon T-222..."}
        │
        ▼ WebSocket → FloatingUI
  [chat_widget.py] akan yazı animasyonu ile gösterir
```

### 5.2 Fiyat Alarm → FloatingUI Bildirimi

```
  [KuroRecon PriceWatcher — alarm.py]
  Fiyat düşüşü tespit edildi!
        │
        ├── Telegram'a gönder   (mevcut)
        │
        └── FloatingBridge'e bildir (yeni)
              │
              ▼ ws://127.0.0.1:9003
        {"type": "alert", "category": "price_alarm",
         "title": "Ford Focus fiyat düştü!",
         "body": "145.000₺ → 138.000₺ (-4.8%)",
         "url": "https://..."}
              │
              ▼
        [FloatingUI — tray_icon + chat_widget]
        Köşe bildirimi + sohbet paneline ekle
```

### 5.3 Sistem Durum Yayını (5 sn'de bir)

```
  [FloatingBridge]
  Her 5 saniyede:
        │
        ├── Llama-server ping  → port 8080 /health
        ├── Walker ping        → port 9002 /health
        └── Chancellor PID     → ps aux | grep chancellor
              │
              ▼
        {"type": "status",
         "llama":     "UP",   "llama_vram": "5.2GB",
         "walker":    "UP",
         "chancellor": "UP",
         "cpu_temp":  "63°C",
         "gpu_temp":  "48°C"}
              │
              ▼
        [status_bar.py] güncelle → küçük gösterge LED'leri
```

---

## 6. UI TASARIM DETAYLARI

### 6.1 Pencere Anatomisi

```
┌──────────────────────────────────────────────────────┐
│ ▣  Kuroshin                              ─  □  ✕   │  ← başlık (sürükle)
├──────────────────────────────────────────────────────┤
│  ● CH  ● LM  ● WK            🌡 CPU:48° GPU:63°    │  ← status_bar
├──────────────────────────────────────────────────────┤
│                                                      │
│  [12 Haz 15:32]                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │ 🤖  Hazır. Ne araştıralım?                  │    │  ← Chancellor mesajı
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │ 👤  bisiklet ara bütçem 3000                │    │  ← Lord mesajı
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │ 🤖  🔍 Epey taranıyor...                    │    │  ← stream (akan yazı)
│  │     ▰▰▰▰▰▱▱▱▱▱  50%                        │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
├──────────────────────────────────────────────────────┤
│  [ Mesajınızı yazın...                    ] [▶] [🎤]│  ← input
├──────────────────────────────────────────────────────┤
│  Opacity: ████████░░  80%     [Gizle] [Ayarlar]     │  ← kontrol şeridi
└──────────────────────────────────────────────────────┘

Boyut: 400×600 px (varsayılan, yeniden boyutlandırılabilir)
Pozisyon: Sağ alt köşe (son pozisyon hafızaya alınır)
```

### 6.2 Renk Paleti & Efektler

```
┌─────────────────────────────────────────────────────────────────┐
│  TEMA: Kuroshin Dark Mica                                       │
│                                                                 │
│  Pencere arka plan: Windows 11 Mica Efekti                      │
│    └── DwmSetWindowAttribute(DWMWA_SYSTEMBACKDROP_TYPE = 2)     │
│    └── Masaüstü bulanık yansıması + koyu katman                 │
│                                                                 │
│  Renk değerleri:                                                │
│  ┌───────────────────────────────────┐                         │
│  │  Arka plan (RGBA): 0, 0, 0, 120  │  ← yarı şeffaf siyah     │
│  │  Başlık çubuğu:   #1A1A2E / 80%  │                         │
│  │  Mesaj balonu:    #16213E / 90%   │                         │
│  │  Kullanıcı balon: #0F3460 / 90%  │                         │
│  │  Vurgu rengi:     #E94560        │  ← Kuroshin kırmızısı    │
│  │  Metin:           #EAEAEA        │                         │
│  │  Stream metin:    #00FF88        │  ← terminal yeşili        │
│  │  Status LED ●:    #00FF88 / ON   │                         │
│  │  Status LED ●:    #FF4444 / OFF  │                         │
│  └───────────────────────────────────┘                         │
│                                                                 │
│  Font: Cascadia Code (monospace, terminal hissi)                │
│  Kenarlık: 1px solid rgba(255,255,255,0.1)                      │
│  Köşe yarıçapı: 12px                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Animasyonlar

```
Akan Yazı (Typewriter Effect):
  Chancellor yanıt gelince → karakter karakter belirir
  Hız: 30ms / karakter (normal), 5ms / karakter (stream hızlı mod)
  QTimer → label.setText(partial_text) döngüsü

Pulse Animasyonu (İşleme Göstergesi):
  Chancellor düşünürken başlık çubuğundaki ● yeşil → sarı → yeşil pulse
  QPropertyAnimation → color interpolation 1.5s döngü

Fade-In (Mesaj Balonu):
  Yeni mesaj gelince balon opacity: 0 → 1, süre: 200ms
  QGraphicsOpacityEffect + QPropertyAnimation

Slide-In (Pencere Açılışı):
  Bat'tan başlatılınca sağ alt köşeden kayarak girer
  Y pozisyonu: ekran_yüksekliği → son_pozisyon, 300ms easing

Bildirim Shake (Fiyat Alarm):
  Pencere 3x yatay sarsılır (5px), 150ms
```

---

## 7. TEKNOLOJİ YIĞINI

```
┌─────────────────────────────────────────────────────────────────┐
│  KARAR: PyQt6 + PyQt-Frameless-Window + win32mica               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Katman          Teknoloji              Neden            │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ UI Framework    PyQt6                  Mevcut stack     │   │
│  │ Pencere efekti  PyQt-Frameless-Window  751★, Mica+Acr.  │   │
│  │ Mica (Win11)    win32mica              121★, minimal    │   │
│  │ Click-through   pywin32 WS_EX_LAYERED  WinAPI native    │   │
│  │ WebSocket       websockets (asyncio)   hızlı, basit     │   │
│  │ Ses bildirimi   playsound              tek satır        │   │
│  │ System tray     PyQt6.QSystemTrayIcon  bağımlılık yok   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Alternatif değerlendirildi ama seçilmedi:                      │
│  ✗ Electron/Tauri: Node.js bağımlılığı, Kuroshin Python stack   │
│  ✗ Tkinter:        Mica/Acrylic efekti yok, görsel yetersiz     │
│  ✗ WPF/WinUI:      C# gerektirir, Python stack dışı            │
│  ✗ CEF/webview:    Chromium bağımlılığı, 100MB+ boyut           │
└─────────────────────────────────────────────────────────────────┘

Gereksinimler (pip):
  PyQt6>=6.6.0
  PyQt-Frameless-Window>=0.3.3
  win32mica>=2.3.0
  websockets>=12.0
  pywin32>=306
  playsound>=1.3.0       (opsiyonel)
```

---

## 8. IPC PROTOKOLÜ (WebSocket Mesaj Formatı)

### 8.1 Bridge → FloatingUI (Sunucu → İstemci)

```json
// Mesaj türleri:

// 1. Chancellor akış mesajı
{
  "type": "stream",
  "chunk": "🔍 Epey taranıyor...",
  "session_id": "abc123",
  "ts": 1718798400
}

// 2. Chancellor tamamlandı
{
  "type": "done",
  "text": "🏆 En iyi 3 ürün bulundu...",
  "session_id": "abc123",
  "ts": 1718798415
}

// 3. Sistem durumu (5 sn'de bir)
{
  "type": "status",
  "chancellor": "UP",
  "llama": "UP",
  "llama_vram_gb": 5.2,
  "walker": "UP",
  "cpu_temp": 48,
  "gpu_temp": 63,
  "ts": 1718798420
}

// 4. Fiyat alarm bildirimi
{
  "type": "alert",
  "category": "price_alarm",
  "title": "Ford Focus fiyat düştü!",
  "body": "145.000₺ → 138.000₺ (-4.8%)",
  "url": "https://www.sahibinden.com/ilan/...",
  "ts": 1718798500
}

// 5. Genel sistem bildirimi
{
  "type": "notify",
  "level": "info",   // info | warn | error
  "text": "Sahibinden cookie'si 7 gün içinde sona eriyor!",
  "ts": 1718798600
}

// 6. Bağlantı onayı
{
  "type": "hello",
  "version": "1.0",
  "auth_ok": true,
  "ts": 1718798400
}
```

### 8.2 FloatingUI → Bridge (İstemci → Sunucu)

```json
// 1. Kimlik doğrulama (bağlantı kurulunca)
{
  "type": "auth",
  "secret": "kuroshin-bridge-2026"
}

// 2. Kullanıcı mesajı (Chancellor'a ilet)
{
  "type": "user_message",
  "text": "bisiklet ara bütçem 3000",
  "ts": 1718798400
}

// 3. Heartbeat (30 sn'de bir)
{
  "type": "ping",
  "ts": 1718798430
}
```

---

## 9. BAT ENTEGRASYONU

### 9.1 Kuroshin.bat Değişikliği

```batch
:: Mevcut [1] Walker Modu'na eklenti:

:START_WALKER_MODE
  :: ... mevcut Chancellor + Llama + Walker başlatma ...

  :: [YENİ] FloatingUI başlat (arka planda, ayrı süreç)
  echo [6/6] FloatingUI baslatiliyor...
  start "Kuroshin FloatingUI" /B pythonw "C:\Kuroshin\kuroshin_floating_ui\main.py"
  timeout /t 2 /nobreak >nul
  echo FloatingUI: BASLATILDI

  :: Bridge (WSL2 tarafı) başlat
  wsl -d Ubuntu-22.04 -- bash -c ^
    "setsid python3 /mnt/c/Kuroshin/scripts/kuroshin_floating_bridge.py ^
     < /dev/null > /tmp/floating_bridge.log 2>&1 & disown"
  echo FloatingBridge: BASLATILDI
```

### 9.2 Bat [5] Kapatma (Android Purge + FloatingUI Kapat)

```batch
:: Mevcut [5] kapatmaya eklenti:
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq Kuroshin FloatingUI" 2>nul
wsl -d Ubuntu-22.04 -- bash -c "pkill -f kuroshin_floating_bridge.py 2>/dev/null"
```

---

## 10. GELİŞTİRME FAZLARI

```
┌─────────────────────────────────────────────────────────────────┐
│  FAZ-1: Temel Pencere (1-2 sohbet)                             │
│  ─────────────────────────────────────────────────────────────  │
│  ✓ PyQt-Frameless-Window kurulumu + Mica efekti                 │
│  ✓ Always-on-top + frameless + şeffaf arka plan                 │
│  ✓ Sürüklenebilir başlık çubuğu                                 │
│  ✓ System tray entegrasyonu (sağ tık: Göster/Gizle/Kapat)       │
│  ✓ Bat'tan başlatma testi                                       │
│  ✓ Pozisyon + opacity ayarları settings.json'a kaydedilir       │
│  ─────────────────────────────────────────────────────────────  │
│  Çıktı: Boş ama güzel görünen, açılıp kapanabilen pencere       │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  FAZ-2: IPC Köprüsü (1-2 sohbet)                               │
│  ─────────────────────────────────────────────────────────────  │
│  ✓ kuroshin_floating_bridge.py WebSocket sunucusu (:9003)       │
│  ✓ FloatingUI WebSocket istemcisi + auth handshake              │
│  ✓ Sistem durum yayını (Chancellor/Llama/Walker LED'leri)       │
│  ✓ Chancellor hook: mesaj gönderince bridge'e bildir            │
│  ✓ Test: bridge → UI → mesaj görünüyor                          │
│  ─────────────────────────────────────────────────────────────  │
│  Çıktı: Gerçek Chancellor mesajları FloatingUI'da görünüyor     │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  FAZ-3: Tam İnteraktif + Animasyonlar (1-2 sohbet)             │
│  ─────────────────────────────────────────────────────────────  │
│  ✓ Input widget → mesaj yaz → Chancellor'a gönder               │
│  ✓ Akan yazı animasyonu (typewriter)                            │
│  ✓ Pulse animasyonu (Chancellor düşünürken)                     │
│  ✓ Fade-in mesaj balonları                                      │
│  ✓ Fiyat alarm bildirimi (shake + köşe popup)                   │
│  ✓ Stream progress bar (market araştırması sırasında)           │
│  ─────────────────────────────────────────────────────────────  │
│  Çıktı: Pluely/Omi kalitesinde tam interaktif FloatingUI        │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  FAZ-4: Gelişmiş Özellikler (isteğe bağlı)                     │
│  ─────────────────────────────────────────────────────────────  │
│  ? Ses bildirimi (playsound)                                    │
│  ? Mikrofon input (SpeechRecognition → Chancellor)              │
│  ? Click-through modu (WS_EX_TRANSPARENT — fareyi geçirir)      │
│  ? Çoklu tema (Light Mica / Dark Mica / Acrylic)                │
│  ? Ekran görüntüsü al → Chancellor'a gönder (multimodal)        │
│  ? Mini mod (sadece status LEDs, 60×20px)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. DOSYA YAPISI (Hedef)

```
C:\Kuroshin\
├── kuroshin_floating_ui/          ← YENİ dizin
│   ├── main.py                    ← pythonw ile başlatılır
│   ├── requirements.txt           ← PyQt6, win32mica, websockets, pywin32
│   ├── settings.json              ← pencere pozisyon, opacity, tema
│   ├── ui/
│   │   ├── floating_window.py
│   │   ├── chat_widget.py
│   │   ├── input_widget.py
│   │   ├── status_bar.py
│   │   └── tray_icon.py
│   ├── core/
│   │   ├── bridge_client.py
│   │   ├── message_model.py
│   │   └── settings.py
│   ├── effects/
│   │   ├── mica_effect.py
│   │   ├── acrylic_effect.py
│   │   └── animations.py
│   └── assets/
│       └── icon.png
│
├── scripts/
│   └── kuroshin_floating_bridge.py   ← YENİ (WSL2 tarafı)
│
└── docs/
    └── FLOATING_UI_MIMARISI.md       ← BU DOSYA
```

---

## 12. TEKNİK RİSKLER & ÇÖZÜMLER

```
┌─────────────────────────────────────────────────────────────────┐
│  Risk                    │ Olasılık │ Çözüm                    │
├─────────────────────────────────────────────────────────────────┤
│  Mica Win10'da çalışmaz  │  DÜŞÜK   │ win32mica Acrylic         │
│  (sadece Win11)          │          │ fallback otomatik         │
├─────────────────────────────────────────────────────────────────┤
│  WebSocket WSL2↔Win bağ. │  ORTA    │ 127.0.0.1:9003 köprü     │
│  sorunları               │          │ auto-reconnect 5s         │
├─────────────────────────────────────────────────────────────────┤
│  Chancellor hook         │  DÜŞÜK   │ send_msg() fonksiyonu     │
│  entegrasyonu çakışması  │          │ zaten var, hook ekle      │
├─────────────────────────────────────────────────────────────────┤
│  PyQt6 asyncio çakışması │  ORTA    │ QThread içinde asyncio    │
│  (WebSocket eventloop)   │          │ yeni event loop aç        │
├─────────────────────────────────────────────────────────────────┤
│  pythonw.exe başlatma    │  DÜŞÜK   │ PATH kontrolü + fallback  │
│  bat'ta bulunamaz        │          │ python -m ile çalıştır    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 13. BAŞARILI TAMAMLANMA KRİTERLERİ

```
FAZ-1 bitti sayılır:
  [ ] Bat [1] ile FloatingUI açılıyor
  [ ] Pencere her zaman üstte duruyor
  [ ] Cam/Mica efekti görünüyor
  [ ] Sürüklenebilir
  [ ] System tray'de ikonu var
  [ ] Bat [5] ile kapanıyor

FAZ-2 bitti sayılır:
  [ ] Bridge WebSocket bağlantısı kuruluyor
  [ ] Chancellor UP/DOWN durumu LED'de görünüyor
  [ ] Bir Chancellor mesajı UI'da görünüyor (canlı kanıt log)

FAZ-3 bitti sayılır:
  [ ] FloatingUI'dan yazılan mesaj Chancellor'a gidiyor
  [ ] Yanıt akan yazıyla geliyor
  [ ] Market araştırması sırasında progress bar dönüyor
  [ ] Fiyat alarm tetiklenince pencere bildirim yapıyor
```

---

## 14. REFERANSLAR

| Proje | Link | Ne için |
|---|---|---|
| PyQt-Frameless-Window | github.com/zhiyiYo/PyQt-Frameless-Window | Mica + Acrylic temel |
| win32mica | pypi.org/project/win32mica | Windows 11 Mica API |
| Pluely (kaynak ilham) | github.com/iamsrikanthnani/pluely | UX pattern referansı |
| Omi macOS | macos.omi.me | Floating bar konsepti |
| ShitStuckToYourMouse | github.com/LtqxWYEG/ShitStuckToYourMouse | Click-through pattern |

---

*Bu belge Floating UI geliştirmesi boyunca güncel tutulacak.*  
*Son güncelleme: 12 Haziran 2026 — Mimari taslak v0.1*
