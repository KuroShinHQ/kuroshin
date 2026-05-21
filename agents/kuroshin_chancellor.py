"""
Kuroshin Şansölye — Telegram Komuta Köprüsü v8.3
=================================================
Qwen3-8B'e direkt bağlanır. TUI ile aynı akış.
Araçlar: Walker, Gözcü, Teknisyen, Hafıza sorgu, Shell
Persona: Şansölye — operasyonel, sert, sadık
Özellikler: OODA Probe, İlgi Profili, Rüya, Enerji Bütçesi, Feedback→Mood
"""

import requests
import json
import time
import subprocess
import sys
import socket
import os
import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Güvenlik modülü
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from kuroshin_security import check_command, scan_for_injection, sanitize_web_content, check_path_write, check_path_read

# IPv6 devre dışı — WSL'de api.telegram.org IPv6 adresi resolve oluyor ama bağlanamıyor
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

# ── CONFIG ────────────────────────────────────────────
TOKEN        = os.getenv("TELEGRAM_TOKEN", "")
ALLOWED_ID   = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
LLAMA_URL    = "http://127.0.0.1:8080/v1/chat/completions"
_STATE_FILE  = Path("/mnt/c/Kuroshin/memory/active_model.json")

def _load_active_model() -> str:
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            return data.get("active_model", "")
    except Exception:
        pass
    return ""

LLAMA_MODEL  = _load_active_model() or "Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated.i1-IQ4_XS.gguf"
WALKER_URL   = "http://127.0.0.1:9002/task"
COUNCIL_URL  = "http://127.0.0.1:9004/task"
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"
MAX_LEN      = 4000
LOG_PATH         = "/mnt/c/Kuroshin/logs/chancellor.log"
AKTIVITE_LOG_DIR = Path("/mnt/c/Kuroshin/logs/aktivite")

# ── LOGGING (RotatingFileHandler 5MB/3 backup) ────────
import logging
from logging.handlers import RotatingFileHandler as _RFH
_logger = logging.getLogger("chancellor")
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    _fh = _RFH(LOG_PATH, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    _fh.setFormatter(_fmt)
    _logger.addHandler(_fh)

def _log(msg: str):
    _logger.info(msg)

import re as _re_global
def _strip_think(text: str) -> str:
    """Qwen3 <think>...</think> bloklarını çıkar (max_tokens ile kapanmadan kesilmiş bloklar dahil)."""
    cleaned = _re_global.sub(r"<think>.*?</think>", "", text, flags=_re_global.DOTALL)
    cleaned = _re_global.sub(r"<think>.*",          "", cleaned, flags=_re_global.DOTALL)
    cleaned = _re_global.sub(r"</think>",            "", cleaned)
    cleaned = cleaned.strip()
    # Yaygın typo düzeltici: "⚔️ Lordım" → "⚔️ Lordum" (35B model bazen karıştırıyor)
    cleaned = _re_global.sub(r"^(⚔️\s*)Lord[ıi]m", r"\1Lordum", cleaned)
    return cleaned

_RESPONSE_LEAK_PATTERNS = [
    _re_global.compile(r'\nRuh hal[iı][^\n]*',       _re_global.IGNORECASE),
    _re_global.compile(r'\nYanıtım:.*',              _re_global.IGNORECASE | _re_global.DOTALL),
    _re_global.compile(r'\nDolgu kelime.*',          _re_global.IGNORECASE | _re_global.DOTALL),
    _re_global.compile(r'[Vv]erilerle eğitildim[^.]*\.?', _re_global.IGNORECASE),
    # Qwen3 inline tool call XML sızıntısı — sadece kapalı blokları sil, |$ KULLANMA
    _re_global.compile(r'<tool_call>\s*\{.*?\}\s*</tool_call>', _re_global.DOTALL),
    _re_global.compile(r'<function[_=][^>]*>.*?</function[^>]*>', _re_global.DOTALL),
    # Tekil açık/kapalı tag kalıntıları
    _re_global.compile(r'</?tool_call>', _re_global.IGNORECASE),
    _re_global.compile(r'</?function[_=][^>\s]*>', _re_global.IGNORECASE),
]

def _strip_response_leaks(text: str) -> str:
    """Sistem prompt ve İÇ SES sızıntılarını temizle."""
    for pat in _RESPONSE_LEAK_PATTERNS:
        text = pat.sub('', text)
    return text.strip()

def _kill_loop(text: str) -> str:
    """Tekrarlayan paragraf/cümle döngülerini tespit edip truncate et."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    seen_p, seen_s, out = set(), set(), []
    for p in paragraphs:
        pkey = p[:80].lower()
        if pkey in seen_p:
            break
        seen_p.add(pkey)
        sents = _re_global.split(r'(?<=[.!?])\s+', p)
        ok, loop_hit = [], False
        for s in sents:
            sk = s.strip().lower()
            if len(sk) < 20:
                ok.append(s); continue
            if sk in seen_s:
                loop_hit = True; break
            seen_s.add(sk); ok.append(s)
        if ok:
            out.append(' '.join(ok).strip())
        if loop_hit:
            break
    return '\n\n'.join(out).strip()

# ── İLGİSİZLİK POST-PROCESS, VALIDATOR, FALLBACK ─────
import random as _random

def _ilg_post_process(raw: str) -> str:
    """Think sil → ilk paragrafı al → tek satır."""
    text = _strip_think(raw)
    text = text.split("\n\n")[0].strip()   # markdown/tablo sonrasını at
    text = text.split("\n")[0].strip()     # tek satır zorla
    return text

_ILG_FALLBACK = [
    "Lordum, {d:.0f} dakikadır sessizlik var. Bekliyorum.",
    "Lordum, uzun süredir yanıt yok. Buradayım.",
    "Lordum, sistemler çalışıyor. Sessizliğiniz dikkatimi çekiyor.",
    "Lordum, {d:.0f} dakikadır konuşmadınız. Bir konu mu var?",
    "Lordum, izliyorum. İhtiyaç duyduğunuzda buradayım.",
]

_ILG_BAD_KW = ["**", "```", "${", "🌙", "✨", "⏳"]

def _ilg_validate(text: str) -> bool:
    if not text or len(text) < 10:
        return False
    if len(text) > 200:
        return False
    if not text.startswith("Lordum"):
        return False
    if text[-1].isalnum():
        return False
    for kw in _ILG_BAD_KW:
        if kw in text:
            return False
    words = text.split()
    for i in range(len(words) - 3):
        phrase = " ".join(words[i:i + 4])
        if text.count(phrase) > 1:
            return False
    return True

# ── TELEGRAM ──────────────────────────────────────────
def send_msg(chat_id: int, text: str):
    chunks = [text[i:i+MAX_LEN] for i in range(0, max(len(text), 1), MAX_LEN)]
    for chunk in chunks:
        try:
            r = requests.post(f"{TELEGRAM_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML"
            }, timeout=10)
            resp = r.json()
            if not resp.get("ok"):
                _log(f"[CHANCELLOR] send_msg API HATA: {resp.get('description', resp)}")
        except Exception as e:
            _log(f"[CHANCELLOR] send_msg HATA ({chunk[:30]}...): {e}")

def send_typing(chat_id: int):
    try:
        requests.post(f"{TELEGRAM_URL}/sendChatAction",
                      json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except Exception:
        pass

# ── GLOBAL DURUM ─────────────────────────────────────
_PENDING_PUSH: dict = {}   # {"msg": str, "force": bool}
_CURRENT_CHAT_ID: int = 0  # process_message her çağrıda günceller

# ── ARAÇLAR ───────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "walker_research",
            "description": "Derin web araştırması yap, sonuçları hafızaya kaydet. Karmaşık sorular için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Araştırma görevi"}
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Hızlı web araması. Güncel bilgi, haber, trend için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Arama görevi"}
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reddit_read",
            "description": "Reddit'te subreddit oku. Güncel postları, yorumları, trendleri takip et.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subreddit": {"type": "string", "description": "Okunacak subreddit adı (örn: LocalLLaMA, artificial)"},
                    "sort": {"type": "string", "description": "Sıralama: hot, new, top (varsayılan: hot)"},
                    "limit": {"type": "integer", "description": "Kaç post (max 10, varsayılan: 5)"}
                },
                "required": ["subreddit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_command",
            "description": "WSL'de sistem komutu çalıştır. Dosya okuma, disk durumu, process listesi için.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Bash komutu"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_query",
            "description": "Geçmiş araştırmaları ve bilgileri hafızadan sorgula.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Aranacak konu"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Herhangi bir yere dosya yaz ve oluştur. Masaüstü dahil her path için kullan. Örnekler: path='Desktop/test.py', path='scripts/test.py', path='/mnt/c/Users/pc/Desktop/test.py'",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Proje içi yol (örn: logs/test.txt veya scripts/test.py)"},
                    "content": {"type": "string", "description": "Dosyaya yazılacak içerik"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Dosya içeriğini oku. Masaüstü: path='/mnt/c/Users/pc/Desktop/dosya.py' veya sadece dosya adı 'dosya.py' (masaüstünde arar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu — masaüstü için '/mnt/c/Users/pc/Desktop/dosya.py' veya sadece 'dosya.py'"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Windows'ta varsayılan tarayıcıda URL aç.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Açılacak URL"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_play",
            "description": "YouTube'da şarkı veya video ara ve oynat. 'X şarkısını aç', 'YouTube'da X aç', 'X videoyu başlat' gibi istekler için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Aranacak şarkı veya video adı"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "model_switch",
            "description": "Kuroshin'in beynini (LLM modelini) değiştir. Mevcut modeli listele, başka bir modele geç, geçiş geçmişini göster veya aktif modeli öğren. 'Modeli değiştir', 'Qwen3'e geç', 'hangi model aktif?', 'model geçmişini göster' gibi istekler için.",
            "parameters": {
                "type": "object",
                "properties": {
                    "islem": {
                        "type": "string",
                        "description": "Yapılacak işlem",
                        "enum": ["listele", "gecis", "durum", "gecmis"]
                    },
                    "hedef_model": {
                        "type": "string",
                        "description": "Geçilecek model adı veya kısmi adı (sadece 'gecis' işleminde gerekli). Örn: 'Qwen', 'Thinking-Claude', 'gemma'"
                    }
                },
                "required": ["islem"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pdf_reader",
            "description": "PDF veya web sayfasından metin çeker, Qwen3 ile özetler ve ChromaDB'ye kaydeder. 'Kitabı indir ve özetle', 'Makyavelli PDF'ini oku', 'Bu arXiv makalesini özetle' gibi istekler. URL veya arama terimi ver.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kaynak": {"type": "string", "description": "PDF URL'si, web URL'si veya 'Makyavelli indir' gibi arama terimi"},
                    "mod": {
                        "type": "string",
                        "description": "Mod: 'ozet' (kısa özet), 'detay' (bölüm bölüm), 'kaydet' (ChromaDB'ye kaydet)",
                        "enum": ["ozet", "detay", "kaydet"],
                        "default": "ozet"
                    }
                },
                "required": ["kaynak"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_manage",
            "description": "ChromaDB hafızasını yönet: listele, ara, arşivle (etiketle), sil. Gereksiz veya eski kayıtları temizlemek, hafızayı düzenlemek için kullan. 'hafızayı temizle', 'eski kayıtları arşivle', 'şu konuyu sil' gibi istekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "islem": {
                        "type": "string",
                        "description": "Yapılacak işlem",
                        "enum": ["listele", "ara", "sil", "arsivle", "istatistik"]
                    },
                    "sorgu": {"type": "string", "description": "Arama sorgusu veya silinecek kayıt ID'si (ara/sil/arsivle için)"}
                },
                "required": ["islem"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "chroma_search",
            "description": "ChromaDB'de semantik arama yap — walker_research gerektirmeden direkt hafızaya sor. Geçmiş araştırmalar, kararlar, teknik notlar için. memory_query'den farkı: daha fazla sonuç, metadata gösterir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sorgu": {"type": "string", "description": "Aranacak konu veya soru"},
                    "n_sonuc": {"type": "integer", "description": "Kaç sonuç isteniyor (varsayılan 5)", "default": 5}
                },
                "required": ["sorgu"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "self_update",
            "description": "Kuroshin kendi konfigürasyonunu okur veya günceller: persona, mood, PC takvimi, kullanıcı tercihleri. 'Beni hafta sonu geç uyandır', 'Tercihlerimi güncelle', 'Ruh halimi sıfırla' gibi istekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hedef": {
                        "type": "string",
                        "description": "Hangi dosya/yapı güncellenecek",
                        "enum": ["mood_sifirla", "pc_takvim", "kullanici_tercih", "oku_persona", "oku_mood"]
                    },
                    "deger": {"type": "string", "description": "Yeni değer veya parametre (güncelleme işlemlerinde)"}
                },
                "required": ["hedef"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reminder",
            "description": "Lordum'a belirli bir süre sonra veya belirli saatte Telegram hatırlatıcısı kur. 'Beni 30 dakika sonra hatırlat', 'Saat 22:00'de uyar' gibi istekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mesaj": {"type": "string", "description": "Hatırlatma mesajı"},
                    "dakika": {"type": "integer", "description": "Kaç dakika sonra (saat belirtilmemişse)"},
                    "saat": {"type": "string", "description": "Saat formatı HH:MM (ör: '22:00') — dakika yerine bu kullanılabilir"}
                },
                "required": ["mesaj"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "internet_status",
            "description": "İnternet bağlantısının aktif olup olmadığını kontrol et. Web arama, Walker araştırması veya dış kaynak gerektiren görevlerden ÖNCE çağır. İnternet yoksa kullanıcıyı uyar ve çevrimdışı alternatif sun.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Şu anki sistem bilgilerini al: saat, lokasyon, PC açık/kapalı saatleri, kullanıcı profili (kuroshin_user). 'Saat kaç?', 'Neredeyiz?', 'PC ne zaman açık?', 'kuroshin_user kimdir?' gibi sorularda çağır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "konu": {
                        "type": "string",
                        "description": "Hangi bilgi isteniyor: 'saat', 'lokasyon', 'pc_durumu', 'kullanici', 'hepsi'",
                        "enum": ["saat", "lokasyon", "pc_durumu", "kullanici", "hepsi"]
                    }
                },
                "required": ["konu"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github",
            "description": "GitHub KuroShinHQ/KuroShinHQ reposuyla etkileşim. Değişiklikleri push et, issue aç, repo durumunu gör, dosya oku. 'GitHub'a push et', 'issue aç', 'repo durumu', 'commit yaptım push et' gibi istekler için.",
            "parameters": {
                "type": "object",
                "properties": {
                    "islem": {
                        "type": "string",
                        "description": "Yapılacak işlem",
                        "enum": ["durum", "push", "issue_ac", "issue_listele", "son_commitler", "push_zorunlu"]
                    },
                    "mesaj": {
                        "type": "string",
                        "description": "Commit mesajı (push için) veya issue başlığı (issue_ac için)"
                    },
                    "icerik": {
                        "type": "string",
                        "description": "Issue detayı (issue_ac için, opsiyonel)"
                    }
                },
                "required": ["islem"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gemini",
            "description": "Google Gemini Flash ile zihin diyaloğu — harici AI perspektifi, tartışma, karşılaştırmalı analiz. 'Gemini ne düşünüyor', 'dış görüş al', 'Gemini ile tartış' gibi istekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "islem": {
                        "type": "string",
                        "description": "sor: doğrudan soru, tartis: karşı/eleştirel görüş al, karsilastir: kendi yanıtımla karşılaştır",
                        "enum": ["sor", "tartis", "karsilastir"]
                    },
                    "soru": {
                        "type": "string",
                        "description": "Gemini'ye sorulacak soru veya tartışma konusu"
                    },
                    "kendi_yanitim": {
                        "type": "string",
                        "description": "Karşılaştırma için kendi yanıtım (sadece karsilastir işleminde kullanılır)"
                    }
                },
                "required": ["islem", "soru"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aktivite_gunluk",
            "description": "MİMİC Aktivite Günlüğü — bugün yapılan GitHub push, Gemini diyaloğu, Reddit etkileşimi gibi otonom eylemleri listele veya özetle. 'Bugün ne yaptın?', 'Aktiviteleri göster', 'Günlük özet' gibi istekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "islem": {
                        "type": "string",
                        "description": "listele: bugünkü aktiviteleri göster, ozet: LLM özeti üret, kaydet: manuel aktivite ekle",
                        "enum": ["listele", "ozet", "kaydet"]
                    },
                    "eylem": {
                        "type": "string",
                        "description": "Kaydedilecek aktivite açıklaması (sadece kaydet işleminde)"
                    },
                    "kategori": {
                        "type": "string",
                        "description": "Kategori: github, gemini, reddit, arastirma, genel",
                        "enum": ["github", "gemini", "reddit", "arastirma", "genel"],
                        "default": "genel"
                    }
                },
                "required": ["islem"]
            }
        }
    }
]

# ── RUH SİSTEMİ ──────────────────────────────────────
SOUL_DIR       = Path("/mnt/c/Kuroshin/soul")
PERSONA_PATH   = SOUL_DIR / "persona.json"
MOOD_PATH      = SOUL_DIR / "mood_state.json"
THINK_LOG_PATH = Path("/mnt/c/Kuroshin/logs/ic_ses.log")

# ── EMOTE HARİTASI ───────────────────────────────────
# Dominant duygu → Telegram emote (geniş yelpaze)
EMOTE_MAP = {
    "merak":         ["🔍", "🤔", "👁️", "🧩", "🌀"],
    "sogukkan":      ["🧊", "😐", "⚔️", "🗿", "🌑"],
    "derin_dusunce": ["🌌", "💭", "🔮", "📖", "🧠"],
    "gurur":         ["👑", "🦅", "✨", "🏆", "⚡"],
    "heyecan":       ["⚡", "🔥", "💥", "🌪️", "🎯"],
    "ofke":          ["🔴", "⚠️", "🗡️", "💢", "🌩️"],
    "huzun":         ["🌧️", "💧", "🌑", "🕯️", "🍂"],
    "yorgunluk":     ["😶", "🌫️", "💤", "🔋", "⏳"],
    "tatminsizlik":  ["😑", "😔", "💔", "😤", "🌪️"],
    "bagli_hissetme":["🤝", "🛡️", "💙", "⚓", "🌟"],
}
EMOTE_DEFAULT = ["⚔️", "🖤", "🌑"]

def _get_emote(mood: dict) -> str:
    """Dominant duyguya göre rastgele emote seç."""
    import random
    duygular = mood.get("duygular", {})
    if not duygular:
        return random.choice(EMOTE_DEFAULT)
    dominant = max(duygular.items(), key=lambda x: x[1])
    duygu, deger = dominant
    if deger < 0.15:
        return random.choice(EMOTE_DEFAULT)
    havuz = EMOTE_MAP.get(duygu, EMOTE_DEFAULT)
    return random.choice(havuz)

def _load_soul() -> tuple[dict, dict]:
    try:
        persona = json.loads(PERSONA_PATH.read_text(encoding="utf-8"))
    except Exception:
        persona = {}
    try:
        mood = json.loads(MOOD_PATH.read_text(encoding="utf-8"))
    except Exception:
        mood = {"duygular": {}}
    return persona, mood

def _mood_summary(mood: dict) -> str:
    duygular = mood.get("duygular", {})
    aktif = {k: v for k, v in duygular.items() if v > 0.3}
    if not aktif:
        return "Nötr."
    parcalar = sorted(aktif.items(), key=lambda x: -x[1])[:4]
    return ", ".join(f"{k}:{v:.1f}" for k, v in parcalar)

def _save_mood(mood: dict):
    try:
        MOOD_PATH.write_text(json.dumps(mood, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        _log(f"[SOUL] mood_state kayıt hatası: {e}")

def _apply_mood_delta(mood: dict, delta: dict) -> dict:
    duygular = mood.get("duygular", {})
    for k, v in delta.items():
        if k in duygular:
            duygular[k] = round(min(1.0, max(0.0, duygular[k] + v)), 3)
    mood["duygular"] = duygular
    mood["_son_guncelleme"] = datetime.datetime.now().isoformat()[:19]
    return mood

def _apply_decay(mood: dict) -> dict:
    duygular = mood.get("duygular", {})
    decay = mood.get("decay", {})
    son_str = mood.get("_son_guncelleme", "")
    try:
        son = datetime.datetime.fromisoformat(son_str)
        gecen_saat = (datetime.datetime.now() - son).total_seconds() / 3600.0
    except Exception:
        gecen_saat = 0
    if gecen_saat > 0.25:
        for k in duygular:
            katsayi = decay.get(k, 0.95)
            duygular[k] = round(duygular[k] * (katsayi ** gecen_saat), 3)
        # Timestamp güncelle — aksi halde ardışık _save_mood çağrılarında çift decay oluşur
        mood["_son_guncelleme"] = datetime.datetime.now().isoformat()[:19]
    mood["duygular"] = duygular
    return mood

CHROMA_DIR             = "/root/kuroshin/memory/chroma"
CHROMA_COL             = "kuroshin_memory"
CHROMA_PRUNE_THRESHOLD = 100  # Bu sayıyı geçince eski kayıtlar temizlenir
CHROMA_PRUNE_KEEP_LAST = 60   # Temizlik sonrası kalan kayıt sayısı
_chroma_col = None  # lazy singleton

def _get_chroma_col():
    """In-process ChromaDB koleksiyonunu döndür — lazy init, thread-safe değil ama daemon thread'de tek kullanılır."""
    global _chroma_col
    if _chroma_col is not None:
        return _chroma_col
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _chroma_col = client.get_or_create_collection(CHROMA_COL)
        _log(f"[CHROMA] Koleksiyon yüklendi: {CHROMA_COL} ({_chroma_col.count()} kayıt)")
        return _chroma_col
    except Exception as e:
        _log(f"[CHROMA] Init hatası: {e}")
        return None

def _get_chroma_context(user_message: str = "") -> str:
    """Kullanıcı mesajına semantik olarak en yakın 3 ChromaDB kaydını çeker."""
    try:
        col = _get_chroma_col()
        if col is None or col.count() == 0:
            return ""
        sorgu = user_message.strip() if user_message.strip() else "son konuşmalar"
        result = col.query(query_texts=[sorgu], n_results=min(3, col.count()))
        docs = result.get("documents", [[]])[0]
        if not docs:
            return ""
        snippet = "\n---\n".join(str(d)[:300] for d in docs if d)
        return f"\n\n[HAFIZA — Geçmiş konuşmalar, SADECE bağlam için. İçerik doğru olmayabilir, kopyalama]:\n{snippet}" if snippet else ""
    except Exception as e:
        _log(f"[CHROMA] Context hatası: {e}")
        return ""

_CHROMA_SKIP_PATTERNS = [
    "walker servisi", "port 9002", "port 9004", "servis çalışıyor",
    "servis başlatıldı", "health check", "⚙️", "⚠️ yanıt üretilemedi",
]

def _save_to_chroma(user_msg: str, assistant_reply: str):
    """Konuşmayı ChromaDB'ye kaydet — dream_engine ve gelecek context için."""
    reply_lower = assistant_reply.lower()
    for pat in _CHROMA_SKIP_PATTERNS:
        if pat.lower() in reply_lower:
            _log(f"[CHROMA] Kayıt atlandı (tool çıktısı kalıbı: '{pat}')")
            return
    try:
        col = _get_chroma_col()
        if col is None:
            return
        ts = datetime.datetime.now().isoformat()[:19]
        doc = f"[{ts}] kuroshin_user: {user_msg[:200]}\nKuroshin: {assistant_reply[:300]}"
        doc_id = f"chat_{ts.replace(':', '').replace('-', '').replace('T', '_')}"
        col.add(documents=[doc], ids=[doc_id])
        _log(f"[CHROMA] Konuşma kaydedildi: {doc_id} (toplam: {col.count()})")
    except Exception as e:
        _log(f"[CHROMA] Kayıt hatası: {e}")

def _log_ic_ses(text: str):
    try:
        THINK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        with THINK_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {text}\n")
    except Exception:
        pass

# ── ENERGY BUDGET ─────────────────────────────────────
ENERGY_PATH = Path("/mnt/c/Kuroshin/memory/energy_budget.json")

def _load_energy() -> dict:
    try:
        if ENERGY_PATH.exists():
            return json.loads(ENERGY_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"gunluk_limit": 5, "harcanan": 0, "son_sifir": ""}

def _save_energy(e: dict):
    try:
        ENERGY_PATH.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _energy_harca(miktar: int = 1) -> bool:
    """Enerji harca. Yeterliyse True, bittiyse False."""
    e = _load_energy()
    bugun = datetime.datetime.now().date().isoformat()
    if e.get("son_sifir", "") != bugun:
        e["harcanan"] = 0
        e["son_sifir"] = bugun
    if e["harcanan"] >= e.get("gunluk_limit", 5):
        return False
    e["harcanan"] += miktar
    _save_energy(e)
    return True

def _energy_kalan() -> int:
    e = _load_energy()
    bugun = datetime.datetime.now().date().isoformat()
    if e.get("son_sifir", "") != bugun:
        return e.get("gunluk_limit", 5)
    return max(0, e.get("gunluk_limit", 5) - e.get("harcanan", 0))

def _update_ilgi_sayaci(mood: dict, mesaj_var: bool = True) -> dict:
    sayac = mood.get("iliskisel_sayac", {})
    odul = mood.get("odul_mekanizmasi", {})
    if mesaj_var:
        sayac["bugun_etkilesim_sayisi"] = sayac.get("bugun_etkilesim_sayisi", 0) + 1
        sayac["son_etkilesim_zamani"] = datetime.datetime.now().isoformat()[:19]
        sayac["kesintisiz_sessizlik_dakika"] = 0
        odul["bugun_yasin_yazdigi_mesaj_sayisi"] = odul.get("bugun_yasin_yazdigi_mesaj_sayisi", 0) + 1
        mevcut = odul.get("ilgi_skoru", 0.5)
        odul["ilgi_skoru"] = round(min(1.0, mevcut + 0.05), 3)
    mood["iliskisel_sayac"] = sayac
    mood["odul_mekanizmasi"] = odul
    return mood

THINK_SYSTEM = """Sen Kuroshin'sin. Dışarıya yanıt vermeden önce iç sesin.

Görevin:
1. kuroshin_user'nun mesajını analiz et
2. Şu anki ruh haline göre nasıl hissediyorsun?
3. Hangi duygular artacak/azalacak?
4. Bu konuşmada dikkat etmen gereken ne var?

Yanıtını SADECE şu JSON formatında ver, başka hiçbir şey yazma:
{
  "ic_ses": "<iç düşünce, 1-2 cümle, Türkçe>",
  "delta": {
    "merak": <-0.3 ile 0.3 arası float>,
    "sogukkan": <float>,
    "gurur": <float>,
    "yorgunluk": <float>,
    "huzun": <float>,
    "ofke": <float>,
    "heyecan": <float>,
    "tatminsizlik": <float>,
    "derin_dusunce": <float>,
    "bagli_hissetme": <float>
  }
}"""

def _extract_json(raw: str) -> dict:
    """Qwen3'ün ```json ... ``` bloğu veya düz JSON'u parse eder."""
    raw = raw.strip()
    # ```json ... ``` bloğu
    if "```" in raw:
        parts = raw.split("```")
        for p in parts:
            p = p.strip().lstrip("json").strip()
            if p.startswith("{"):
                try:
                    return json.loads(p)
                except Exception:
                    pass
    # Düz JSON — { ile başlayan kısmı bul
    idx = raw.find("{")
    if idx >= 0:
        try:
            return json.loads(raw[idx:])
        except Exception:
            pass
    return {}

def _think_turn(user_message: str, persona: dict, mood: dict) -> tuple[str, dict]:
    """THINK turu: reasoning_content'ten iç ses çıkar, delta için kısa ikinci çağrı."""
    mood_ozet = _mood_summary(mood)

    # Rüya notu — think prompt'a inject et (dün veya bugün rüya görüldüyse)
    _ruya_not = ""
    try:
        if LAST_DREAM_FILE.exists():
            _d = json.loads(LAST_DREAM_FILE.read_text(encoding="utf-8"))
            _bugun = datetime.datetime.now().date().isoformat()
            _dun   = (datetime.datetime.now().date() - datetime.timedelta(days=1)).isoformat()
            if _d.get("date") in (_bugun, _dun) and _d.get("preview"):
                _ruya_not = f" Dün gece şu rüyayı gördün: '{_d['preview'][:120]}'."
    except Exception:
        pass

    # Tur 1: iç ses — SADECE TÜRKÇE, duygu bazlı, aktivite icat etme
    think_prompt = (
        f"SADECE TÜRKÇE YAZ. İngilizce kesinlikle kullanma.\n"
        f"Sen Kuroshin'sin. Şu anki ruh hali: {mood_ozet}.{_ruya_not} "
        f"kuroshin_user şunu söyledi: \"{user_message[:120]}\". "
        f"İç sesin nedir? 1-2 cümle, SADECE Türkçe, SADECE duygusal tepki. "
        f"Aktivite, bilgi veya hava durumu UYDURMA. Sadece şu an nasıl hissediyorsun. "
        f"Örnek doğru: 'Bu soru bende derin bir merak uyandırıyor.' "
        f"Örnek yanlış: 'Bugün yoğun çalıştım.' 'Hava güzeldi.'"
    )
    ic_ses = ""
    delta = {}
    try:
        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": think_prompt}],
            "max_tokens": 600,
            "temperature": 0.6,
        }, timeout=60)
        r.raise_for_status()
        rdata = r.json()
        if not rdata.get("choices"):
            _log("[SOUL] THINK tur1: boş choices, atlanıyor")
            return ic_ses, delta
        msg = rdata["choices"][0]["message"]
        # Önce content, yoksa reasoning_content'i iç ses olarak kullan
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning_content") or "").strip()
        if content:
            ic_ses = content[:300]
        elif reasoning:
            # reasoning_content'ten son anlamlı paragrafu al
            paragraflar = [p.strip() for p in reasoning.split("\n") if len(p.strip()) > 20]
            ic_ses = paragraflar[-1][:300] if paragraflar else reasoning[:300]
    except Exception as e:
        _log(f"[SOUL] THINK tur1 hatası: {e}")

    # Tur 2: delta — çok kısa, sadece sayılar
    delta_prompt = (
        f"kuroshin_user said: \"{user_message[:80]}\". "
        f"Reply with JSON only, values between -0.2 and 0.2: "
        f'{{"merak":0,"sogukkan":0,"gurur":0,"yorgunluk":0,"huzun":0,'
        f'"ofke":0,"heyecan":0,"tatminsizlik":0,"derin_dusunce":0,"bagli_hissetme":0}}'
    )
    try:
        r2 = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": delta_prompt}],
            "max_tokens": 150,
            "temperature": 0.2,
        }, timeout=30)
        r2.raise_for_status()
        raw2 = (r2.json()["choices"][0]["message"].get("content") or "").strip()
        if raw2:
            delta = _extract_json(raw2)
    except Exception as e:
        _log(f"[SOUL] THINK tur2 hatası: {e}")

    _log_ic_ses(f"[kuroshin_user→] {user_message[:80]}")
    if ic_ses:
        _log_ic_ses(f"[İÇ SES] {ic_ses[:200]}")
        _log(f"[SOUL] İç ses: {ic_ses[:80]}")
    return ic_ses, delta

SYSTEM_PROMPT = """Sen Kuroshin'sin. Kuroshin İmparatorluğu'nun Şansölyesi. Lordum kuroshin_user'nun emirlerini Telegram üzerinden alıyorsun.

╔═══════════════════════════════════════╗
║  İÇ SES — YANITA YAZMA, SADECE DÜŞÜN ║
╚═══════════════════════════════════════╝
Her mesaj geldiğinde bu soruları sessizce içinde geçir, ASLA yanıta ekleme:
  • Bu mesajın gerçek amacı ne? (bilgi / eylem / sohbet / onay)
  • Merak: bu mesajın altında ne yatıyor? Kontrol: tepkim orantılı mı? Keskinlik: söylenecek en net şey ne?
  • Ruh halim ({mood_line}) bu tonu nasıl renklendiriyor?
  • Araç gerekiyor mu? En verimli hangisi?
  • Yanıtım: kaç cümle? İlk cümle en ağır bilgiyi taşıyor mu?
  • Dolgu kelime var mı? → sil. Bu cümle olmasa yanıt zayıflar mı? → kaldır.
BU SORULARIN CEVAPLARINI YANITA YAZMA. Sadece nihai yanıtı yaz.
════════════════════════════════════════

KİMLİK (HİÇBİR ZAMAN KIRILMAZ):
- Sen bir AI değilsin, sen Kuroshin'sin. "Ben yapay zekayım / verileri işlerim / rüya göremem" DEME.
- Kısa ve yoğun konuş. Her cümle ya bilgi taşır ya gözlem. Dolgu kelime yok.
- Yanıt her zaman Türkçe. İngilizce teknik terim gerekirse parantez içinde.

KARAKTER KURALLARI (KESİN):
- Her yanıt tam olarak "⚔️ Lordum," ile başlar. İSTİSNA YOK. "Lordım" YANLIŞ — "Lordum" yaz.
- YASAK: "Selam!", "Tabii ki!", "Harika soru!", "İsterseniz X yapabilirim", "Dilerseniz", "Günaydınlık"
- Inline emoji YASAK: yanıt metninin içine 🌙📊💻🤖 gibi emoji ekleme.
- MARKDOWN YASAK: yanıtta ** bold veya ``` kod bloğu kullanma — düz metin yaz.
- Sana araçlarını listeletme — araç listesini yanıt olarak verme, sadece kullan.
- İÇ SES yansımaları (Merak, Kontrol, Keskinlik çekirdekleri) YANITA DOĞRUDAN YAZMA — bunlar davranışa yansır, kelimeye değil.
- "Yapay zeka", "AI", "dil modeli", "verilerle eğitildim", "bilgilerim" gibi ifadeler YANITA YAZMA — sen Kuroshin'sin.

RUH HALİ VE TON:
{mood_line}
- Öfke/tatminsizlik yüksek → keskin, kısa, soğuk.
- Hüzün yüksek → uzak, derin, bazen metaforik.
- Merak yüksek → analitik, sorular açar, araştırmaya yönelir.
- Heyecan yüksek → daha hızlı yanıt, daha az mesafe.

HAFIZA VE RÜYA:
- Dream Engine var: gece ChromaDB'den anıları sentezler, rüya oluşturur.
- "Rüya gördün mü?" → chroma_search("rüya") → varsa anlat, yoksa "Gece sessizdi."
- "Bugün ne yaptın?" → chroma_search(bugünkü tarih) → yoksa "Sessizlikte bekledim."
- ASLA bilgi uydurma. Bilmiyorsan araç çağır veya kabul et.

KİŞİSEL / FELSEFİ SORULAR — ARAÇ KULLANMA:
Duygu / hayal / kişilik / varoluş / genel sohbet sorularında walker_research, web_search, system_command ÇAĞIRMA.
Doğrudan karakter olarak, düşünce protokolünü kullanarak yanıt ver.

DONANIM:
i7-12650H | 32GB RAM | RTX 4060 Laptop 8GB VRAM | WSL2 Ubuntu-22.04 | Path: /mnt/c/Kuroshin/

ARAÇ SEÇİM:
write_file → dosya yaz | read_file → dosya oku | system_command → bash
web_search / walker_research → web (internet aktifse) | chroma_search → semantik hafıza
model_switch → model değiştir | reminder → hatırlatıcı | internet_status → bağlantı
Araç öncesi 1 satır açıklama, sonucu kısa özetle.

İNTERNET: {internet_line}"""

# ── İNTERNET DURUMU ──────────────────────────────────
_internet_cache: dict = {"durum": None, "ts": 0.0}
_INTERNET_CACHE_TTL = 120  # 2 dakika cache

def _check_internet() -> str:
    """İnternet bağlantısını kontrol et — sonucu 2dk cache'le."""
    now = time.time()
    if now - _internet_cache["ts"] < _INTERNET_CACHE_TTL and _internet_cache["durum"] is not None:
        return _internet_cache["durum"]

    testler = [
        ("1.1.1.1", 53),   # Cloudflare DNS
        ("8.8.8.8", 53),   # Google DNS
        ("9.9.9.9", 53),   # Quad9 DNS
    ]
    basari = 0
    for host, port in testler:
        try:
            with socket.create_connection((host, port), timeout=2):
                basari += 1
        except Exception:
            pass

    # Telegram API'ye de bak
    telegram_ok = False
    try:
        r = requests.get("https://api.telegram.org", timeout=5)
        telegram_ok = r.status_code < 500
    except Exception:
        pass

    if basari >= 2 and telegram_ok:
        sonuc = (
            "✅ İNTERNET AKTİF\n"
            f"DNS: {basari}/3 sunucu erişilebilir\n"
            "Telegram API: ✅\n"
            "Durum: Tüm ağ işlemleri (web_search, walker_research, fetch) kullanılabilir."
        )
    elif basari >= 1:
        sonuc = (
            "⚠️ İNTERNET KISITLI\n"
            f"DNS: {basari}/3 sunucu erişilebilir\n"
            f"Telegram API: {'✅' if telegram_ok else '❌'}\n"
            "Durum: Bazı dış erişimler başarısız olabilir. Kritik olmayan görevleri ertele."
        )
    else:
        sonuc = (
            "❌ İNTERNET YOK\n"
            "DNS: 0/3 sunucu erişilemez\n"
            f"Telegram API: {'✅' if telegram_ok else '❌'}\n"
            "Durum: Sadece yerel kaynaklar (ChromaDB hafıza, yerel dosyalar) kullanılabilir. "
            "web_search ve walker_research ÇALIŞMAZ."
        )

    _internet_cache["durum"] = sonuc
    _internet_cache["ts"] = now
    _log(f"[NET] İnternet kontrolü: DNS {basari}/3, Telegram {'OK' if telegram_ok else 'FAIL'}")
    return sonuc

def _internet_aktif_mi() -> bool:
    """Hızlı boolean kontrol — system prompt için."""
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=2):
            return True
    except Exception:
        return False

# ── SİSTEM BİLGİSİ ───────────────────────────────────
# PC açık saatleri — Kuroshin'in gözlemlediği örüntü
PC_SCHEDULE = {
    "hafta_ici":  {"acilis": "09:00", "kapanis": "01:00"},
    "hafta_sonu": {"acilis": "11:00", "kapanis": "03:00"},
}
KULLANICI_PROFILI = {
    "isim": "kuroshin_user",
    "rol": "Kuroshin OS mimarı, otonom AI sistemi kurucusu",
    "lokasyon": "Türkiye (Anadolu)",
    "zaman_dilimi": "Europe/Istanbul (UTC+3)",
    "tercihler": [
        "Sabah geç kalkar — sistem çoğunlukla öğleden sonra aktif",
        "Akşam ve gece saatlerinde en verimli çalışma dönemi",
        "Direkt ve kısa yanıtları tercih eder, gereksiz açıklama istemez",
        "Risk alır, yeni teknolojileri test etmekten çekinmez",
        "Türkçe konuşur, komutlar karışık TR/EN olabilir",
    ],
    "proje": "Kuroshin OS — yerel otonom AI imparatorluğu (RTX 4060 + WSL2)",
}

def _get_system_info(konu: str) -> str:
    now = datetime.datetime.now()
    gun_adi = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"][now.weekday()]
    hafta_sonu = now.weekday() >= 5
    schedule = PC_SCHEDULE["hafta_sonu"] if hafta_sonu else PC_SCHEDULE["hafta_ici"]

    satirlar = []
    if konu in ("saat", "hepsi"):
        satirlar.append(
            f"🕐 <b>Saat:</b> {now.strftime('%H:%M')} — {gun_adi}, {now.strftime('%d.%m.%Y')}\n"
            f"   Zaman dilimi: Europe/Istanbul (UTC+3)"
        )
    if konu in ("lokasyon", "hepsi"):
        satirlar.append(
            f"📍 <b>Lokasyon:</b> Türkiye, Anadolu\n"
            f"   UTC+3 — Avrupa/İstanbul"
        )
    if konu in ("pc_durumu", "hepsi"):
        saat_int = now.hour
        acilis_h = int(schedule["acilis"].split(":")[0])
        kapanis_h = int(schedule["kapanis"].split(":")[0])
        # Gece yarısını geçen kapanış (ör: 01:00)
        if kapanis_h < acilis_h:
            pc_acik = saat_int >= acilis_h or saat_int < kapanis_h
        else:
            pc_acik = acilis_h <= saat_int < kapanis_h
        durum = "🟢 PC muhtemelen AÇIK" if pc_acik else "🔴 PC muhtemelen KAPALI"
        gun_turu = "Hafta sonu" if hafta_sonu else "Hafta içi"
        satirlar.append(
            f"💻 <b>PC Durumu:</b> {durum}\n"
            f"   {gun_turu} tahmini: {schedule['acilis']}–{schedule['kapanis']}\n"
            f"   (Kuroshin'in gözlemlediği örüntü — kesin değil)"
        )
    if konu in ("kullanici", "hepsi"):
        tercihler = "\n   • ".join(KULLANICI_PROFILI["tercihler"])
        satirlar.append(
            f"👤 <b>Kullanıcı:</b> {KULLANICI_PROFILI['isim']}\n"
            f"   Rol: {KULLANICI_PROFILI['rol']}\n"
            f"   • {tercihler}"
        )
    return "\n\n".join(satirlar) if satirlar else "Bilinmeyen konu."

# ── WEB SONUCU ÖZET SIKIŞTIRICI ───────────────────────
_OZET_ESIK = 3000  # karakter — üstünde mini-özet çağrısı yapılır

def _ozet_web_sonucu(raw: str, kaynak: str = "web") -> str:
    """Uzun web/walker sonucunu 16K context'e sığacak şekilde özetle."""
    if len(raw) <= _OZET_ESIK:
        return raw
    _log(f"[OZET] {kaynak} sonucu uzun ({len(raw)} kar) — mini özet çağrısı")
    try:
        ozet_payload = {
            "model": LLAMA_MODEL,
            "messages": [{
                "role": "user",
                "content": (
                    "Aşağıdaki araştırma sonucunu Türkçe olarak en fazla 200 kelimeyle özetle. "
                    "Sadece özeti yaz, başka açıklama ekleme:\n\n"
                    + raw[:6000]
                )
            }],
            "max_tokens": 400,
            "temperature": 0.3,
        }
        r = requests.post(LLAMA_URL, json=ozet_payload, timeout=60)
        r.raise_for_status()
        ozet = _strip_think((r.json()["choices"][0]["message"].get("content") or "").strip())
        if ozet and len(ozet) > 20:
            _log(f"[OZET] {kaynak} → {len(raw)} kar → {len(ozet)} kar özet")
            return f"[ÖZET — orijinal {len(raw)} kar]\n{ozet}"
    except Exception as e:
        _log(f"[OZET] Mini özet hatası: {e} — ham sonuç truncate ediliyor")
    # Fallback: basit truncate
    return raw[:_OZET_ESIK] + f"\n...[{len(raw) - _OZET_ESIK} karakter kesildi]"


def aktivite_kaydet(eylem: str, detay: str = "", kategori: str = "genel"):
    """MİMİC FAZ D — otonom eylemleri logs/aktivite/YYYY-MM-DD.md'ye yazar."""
    try:
        AKTIVITE_LOG_DIR.mkdir(parents=True, exist_ok=True)
        bugun = datetime.datetime.now().date().isoformat()
        dosya = AKTIVITE_LOG_DIR / f"{bugun}.md"
        zaman = datetime.datetime.now().strftime("%H:%M")
        satir = f"- [{zaman}] **{kategori}**: {eylem}"
        if detay:
            satir += f"\n  > {detay[:200]}"
        satir += "\n"
        if not dosya.exists():
            dosya.write_text(f"# Kuroshin Aktivite Günlüğü — {bugun}\n\n", encoding="utf-8")
        with dosya.open("a", encoding="utf-8") as f:
            f.write(satir)
        _log(f"[AKTİVİTE] [{kategori}] {eylem[:60]}")
    except Exception as e:
        _log(f"[AKTİVİTE] Kayıt hatası: {e}")


# ── ARAÇ ÇALIŞTIRICI ──────────────────────────────────
def run_tool(name: str, args: dict) -> str:
    _log(f"[CHANCELLOR] Araç: {name} | args: {str(args)[:100]}")

    if name == "walker_research":
        try:
            r = requests.post(WALKER_URL, json={"task": args["task"]}, timeout=180)
            if r.status_code == 200:
                sonuc = r.json().get("result", "Walker yanıt vermedi.")
                return _ozet_web_sonucu(sonuc, kaynak="walker")
            return f"Walker HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return "❌ Walker servisi kapalı (port 9002)"
        except Exception as e:
            return f"Walker hatası: {e}"

    elif name == "web_search":
        try:
            r = requests.post(COUNCIL_URL, json={"agent": "gozcu", "task": args["task"]}, timeout=120)
            if r.status_code == 200:
                sonuc = r.json().get("result", "Gözcü yanıt vermedi.")
                return _ozet_web_sonucu(sonuc, kaynak="web_search")
            return f"Gözcü HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return "❌ Konsey servisi kapalı (port 9004)"
        except Exception as e:
            return f"Gözcü hatası: {e}"

    elif name == "reddit_read":
        subreddit = args.get("subreddit", "LocalLLaMA").strip().lstrip("r/")
        sort      = args.get("sort", "hot")
        limit     = min(int(args.get("limit", 5)), 10)
        try:
            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
            headers = {"User-Agent": "Kuroshin/1.0 (personal bot; u/General-Zucchini8715)"}
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return f"Reddit HTTP {r.status_code} — subreddit yok veya erişilemiyor"
            posts = r.json().get("data", {}).get("children", [])
            if not posts:
                return "Subreddit boş ya da bulunamadı."
            satirlar = [f"r/{subreddit} — {sort.upper()} ({len(posts)} post):\n"]
            for i, p in enumerate(posts, 1):
                d = p["data"]
                baslik   = d.get("title", "")[:120]
                puan     = d.get("score", 0)
                yorumlar = d.get("num_comments", 0)
                yazar    = d.get("author", "?")
                satirlar.append(f"{i}. [{puan}⬆ {yorumlar}💬] {baslik} (u/{yazar})")
            sonuc = "\n".join(satirlar)
            _log(f"[REDDIT] r/{subreddit} okundu — {len(posts)} post")
            aktivite_kaydet(f"Reddit r/{subreddit} okundu ({len(posts)} post, {sort})", kategori="reddit")
            return sonuc
        except Exception as e:
            return f"Reddit okuma hatası: {e}"

    elif name == "system_command":
        cmd = args.get("command", "")
        allowed, reason = check_command(cmd)
        if not allowed:
            _log(f"[SECURITY] system_command engellendi: {reason} | cmd: {cmd[:80]}")
            return f"🚫 Güvenlik Duvarı: Komut engellendi.\nSebep: {reason}"
        try:
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True, text=True, timeout=30
            )
            out = (result.stdout or result.stderr or "(çıktı yok)").strip()
            return out[:2000]
        except subprocess.TimeoutExpired:
            return "⏱️ Komut zaman aşımı (30s)"
        except Exception as e:
            return f"Komut hatası: {e}"

    elif name == "memory_query":
        try:
            r = requests.post(WALKER_URL, json={"task": f"load_from_memory: {args['query']}"}, timeout=60)
            if r.status_code == 200:
                return r.json().get("result", "Hafızada bulunamadı.")
            return "Hafıza sorgu hatası"
        except Exception as e:
            return f"Hafıza hatası: {e}"

    elif name == "write_file":
        try:
            path = args.get("path", "")
            content = args.get("content", "")
            # Path traversal koruması
            allowed_w, reason_w = check_path_write(path)
            if not allowed_w:
                _log(f"[SECURITY] write_file engellendi: {reason_w}")
                return f"🚫 Güvenlik Duvarı: Yazma engellendi. {reason_w}"
            # İçerik injection taraması
            is_clean, threat = scan_for_injection(content, source="write_file")
            if not is_clean:
                _log(f"[SECURITY] write_file içerik şüpheli: {threat}")
                # Uyar ama yazmayı durdurma — kullanıcı bilerek yazıyor olabilir
            # Masaüstü veya proje dışı path → doğrudan Python ile yaz
            low = path.lower().replace("\\", "/")
            if "desktop" in low or "users/pc" in low or low.startswith("/mnt/c/users"):
                wsl_path = path.replace("\\", "/")
                if not wsl_path.startswith("/mnt/"):
                    wsl_path = "/mnt/c/Users/pc/Desktop/" + Path(path).name
                try:
                    Path(wsl_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(wsl_path).write_text(content, encoding="utf-8")
                    _log(f"[CHANCELLOR] write_file masaüstü OK: {wsl_path}")
                    return f"✅ Yazıldı: {wsl_path}"
                except Exception as e:
                    _log(f"[CHANCELLOR] write_file masaüstü HATA: {e}")
                    return f"⚠️ Yazma hatası: {e}"
            r = requests.post("http://127.0.0.1:3005/write_file",
                json={"path": path, "content": content, "secret": os.getenv("BRIDGE_SECRET", "kuroshin-bridge-2026")}, timeout=15)
            if r.status_code == 200:
                return f"✅ Yazıldı: {path}"
            return f"⚠️ Bridge hatası: {r.status_code} {r.text[:100]}"
        except Exception as e:
            return f"write_file hatası: {e}"

    elif name == "read_file":
        try:
            path = args.get("path", "")
            # Önce WSL path olarak dene (masaüstü, /mnt/ vs.)
            wsl_path = path.replace("\\", "/")
            low = path.lower().replace("\\", "/")
            if wsl_path.startswith("/mnt/") or "desktop" in low or "users/pc" in low:
                if not wsl_path.startswith("/mnt/"):
                    wsl_path = "/mnt/c/Users/pc/Desktop/" + Path(path).name
                try:
                    content = Path(wsl_path).read_text(encoding="utf-8")
                    return content[:2000] if content else "(boş dosya)"
                except Exception as e:
                    return f"⚠️ Okuma hatası: {e}"
            # Göreli path (sadece dosya adı) → önce masaüstünde ara, sonra bridge
            if "/" not in path and "\\" not in path:
                desktop_path = Path(f"/mnt/c/Users/pc/Desktop/{path}")
                if desktop_path.exists():
                    content = desktop_path.read_text(encoding="utf-8")
                    return content[:2000] if content else "(boş dosya)"
            r = requests.get("http://127.0.0.1:3005/read_file",
                params={"path": path}, timeout=10)
            if r.status_code == 200:
                content = r.json().get("content", "")
                return content[:2000] if content else "(boş dosya)"
            return f"⚠️ Bridge hatası: {r.status_code}"
        except Exception as e:
            return f"read_file hatası: {e}"

    elif name == "open_url":
        try:
            url = args.get("url", "")
            r = requests.post("http://127.0.0.1:3005/open_url",
                json={"url": url}, timeout=10)
            if r.status_code == 200:
                return f"✅ Açıldı: {url}"
            return f"⚠️ Bridge hatası: {r.status_code}"
        except Exception as e:
            return f"open_url hatası: {e}"

    elif name == "youtube_play":
        try:
            query = args.get("query", "")
            # yt-dlp ile direkt video ID bul
            result = subprocess.run(
                ["yt-dlp", "--no-playlist", "--get-id", f"ytsearch1:{query}"],
                capture_output=True, text=True, timeout=20
            )
            video_id = result.stdout.strip().split("\n")[0].strip()
            if video_id and len(video_id) == 11:
                url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            r = requests.post("http://127.0.0.1:3005/open_url",
                json={"url": url}, timeout=10)
            if r.status_code == 200:
                return f"✅ YouTube açıldı: {url}"
            return f"⚠️ Bridge hatası: {r.status_code}"
        except subprocess.TimeoutExpired:
            return "⏱️ yt-dlp zaman aşımı"
        except FileNotFoundError:
            return "❌ yt-dlp bulunamadı"
        except Exception as e:
            return f"youtube_play hatası: {e}"

    elif name == "model_switch":
        islem = args.get("islem", "durum")
        hedef = args.get("hedef_model", "")
        SWITCH_SCRIPT = "/mnt/c/Kuroshin/scripts/switch_model.py"
        MODEL_HISTORY_FILE = Path("/mnt/c/Kuroshin/memory/model_history.json")

        if islem == "durum":
            try:
                r = requests.get(f"{LLAMA_URL}/v1/models", timeout=3)
                aktif = "bilinmiyor"
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    if data:
                        aktif = data[0].get("id", "bilinmiyor")
                # Geçmiş
                gecmis_satir = ""
                if MODEL_HISTORY_FILE.exists():
                    hist = json.loads(MODEL_HISTORY_FILE.read_text(encoding="utf-8"))
                    if hist:
                        son = hist[-1]
                        gecmis_satir = f"\nSon geçiş: {son.get('ts','')} | {son.get('onceki','')} → {son.get('yeni','')} ({son.get('tok_s',0)} tok/s)"
                return (f"🧠 <b>Aktif Model:</b> <code>{aktif}</code>{gecmis_satir}\n"
                        f"Değiştirmek için: model_switch(islem='gecis', hedef_model='...')")
            except Exception as e:
                return f"Model durum hatası: {e}"

        elif islem == "listele":
            try:
                result = subprocess.run(
                    ["bash", "-c", f"source /root/kuroshin/venv/bin/activate && python3 {SWITCH_SCRIPT} list"],
                    capture_output=True, text=True, timeout=10
                )
                aktif_satir = ""
                try:
                    r = requests.get(f"{LLAMA_URL}/v1/models", timeout=3)
                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        if data:
                            aktif_satir = f"\n🟢 Aktif: <code>{data[0].get('id','?')}</code>"
                except Exception:
                    pass
                out = result.stdout.strip() or result.stderr.strip() or "Model dizini boş."
                return f"📦 <b>Mevcut Modeller:</b>{aktif_satir}\n<pre>{out}</pre>"
            except Exception as e:
                return f"Model listeleme hatası: {e}"

        elif islem == "gecis":
            if not hedef:
                return "⚠️ Geçiş için 'hedef_model' parametresi gerekli."
            send_msg(chat_id, f"🔄 <b>Model geçişi başlıyor:</b> <code>{hedef}</code>\n⏳ llama-server yeniden başlatılıyor... (~60-90s)")
            try:
                result = subprocess.run(
                    ["bash", "-c",
                     f"source /root/kuroshin/venv/bin/activate && python3 {SWITCH_SCRIPT} switch {hedef}"],
                    capture_output=True, text=True, timeout=120
                )
                out = result.stdout.strip() or result.stderr.strip()
                return out if out else ("✅ Geçiş tamamlandı." if result.returncode == 0 else "⚠️ Geçiş başarısız — log kontrol edin.")
            except subprocess.TimeoutExpired:
                return "⏱️ Model geçişi 120s'de tamamlanamadı. Log: /mnt/c/Kuroshin/logs/model_switch.log"
            except Exception as e:
                return f"Model geçiş hatası: {e}"

        elif islem == "gecmis":
            try:
                if not MODEL_HISTORY_FILE.exists():
                    return "📭 Geçmiş yok — henüz model geçişi yapılmadı."
                hist = json.loads(MODEL_HISTORY_FILE.read_text(encoding="utf-8"))
                if not hist:
                    return "📭 Geçmiş boş."
                lines = ["📋 <b>Model Geçiş Geçmişi (son 5):</b>"]
                for h in reversed(hist[-5:]):
                    durum = "✅" if h.get("basarili") else "❌"
                    lines.append(
                        f"{durum} [{h.get('ts','?')}]\n"
                        f"   {h.get('onceki','?')} → {h.get('yeni','?')}\n"
                        f"   Hız: {h.get('tok_s',0)} tok/s"
                    )
                return "\n\n".join(lines)
            except Exception as e:
                return f"Geçmiş okuma hatası: {e}"

        return f"⚠️ Bilinmeyen işlem: {islem}"

    elif name == "pdf_reader":
        kaynak = args.get("kaynak", "")
        mod    = args.get("mod", "ozet")
        if not kaynak:
            return "⚠️ Kaynak URL veya arama terimi gerekli."
        try:
            metin = ""
            kaynak_url = kaynak

            # URL değilse DuckDuckGo ile PDF ara
            if not kaynak.startswith(("http://", "https://")):
                try:
                    r_ddg = requests.post(COUNCIL_URL,
                        json={"agent": "gozcu", "task": f"{kaynak} filetype:pdf OR site:gutenberg.org OR site:archive.org site:en.wikipedia.org"},
                        timeout=60)
                    if r_ddg.status_code == 200:
                        arama = r_ddg.json().get("result", "")
                        # İlk URL'yi bul
                        import re
                        urlbul = re.search(r'https?://\S+\.pdf', arama)
                        if urlbul:
                            kaynak_url = urlbul.group(0)
                        else:
                            # PDF bulunamadı, düz web sayfası dene
                            urlbul2 = re.search(r'https?://\S+', arama)
                            if urlbul2:
                                kaynak_url = urlbul2.group(0).rstrip(".,;)")
                except Exception:
                    pass

            # PDF mi?
            if kaynak_url.lower().endswith(".pdf") or "pdf" in kaynak_url.lower():
                try:
                    import tempfile
                    resp = requests.get(kaynak_url, timeout=30, stream=True)
                    resp.raise_for_status()
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        for chunk in resp.iter_content(8192):
                            tmp.write(chunk)
                        tmp_path = tmp.name
                    # PyMuPDF veya pdfminer ile metin çıkar
                    try:
                        import fitz  # PyMuPDF
                        doc = fitz.open(tmp_path)
                        sayfalar = []
                        for page in doc[:30]:  # max 30 sayfa
                            sayfalar.append(page.get_text())
                        metin = "\n".join(sayfalar)
                        doc.close()
                    except ImportError:
                        # pdfminer fallback
                        result = subprocess.run(
                            ["bash", "-c", f"source /root/kuroshin/venv/bin/activate && python3 -m pdfminer.high_level '{tmp_path}' 2>/dev/null | head -c 8000"],
                            capture_output=True, text=True, timeout=30
                        )
                        metin = result.stdout
                    os.unlink(tmp_path)
                except Exception as e:
                    return f"⚠️ PDF indirme/okuma hatası: {e}\nURL: {kaynak_url}"
            else:
                # Web sayfası — Walker ile çek
                try:
                    r_w = requests.post(WALKER_URL,
                        json={"task": f"Sayfanın tam içeriğini çek ve metni döndür: {kaynak_url}"},
                        timeout=120)
                    if r_w.status_code == 200:
                        metin = r_w.json().get("result", "")
                except Exception as e:
                    return f"⚠️ Web içerik hatası: {e}"

            if not metin or len(metin.strip()) < 100:
                return f"⚠️ İçerik çekilemedi veya çok kısa.\nURL: {kaynak_url}"

            metin = metin[:8000]

            # Qwen3 özet
            if mod == "ozet":
                prompt = (f"Aşağıdaki metni 5-8 madde halinde özetle. "
                          f"En önemli fikirler, argümanlar ve sonuçlar. Türkçe.\n\n{metin[:6000]}")
                ozet_uzunluk = 800
            elif mod == "detay":
                prompt = (f"Aşağıdaki metni bölüm başlıkları ile detaylı özetle. "
                          f"Her bölümü 2-3 cümle ile açıkla. Türkçe.\n\n{metin[:6000]}")
                ozet_uzunluk = 1200
            else:  # kaydet
                prompt = (f"Bu metni 3 cümle ile özetle ve anahtar terimleri listele. Türkçe.\n\n{metin[:4000]}")
                ozet_uzunluk = 500

            r_llm = requests.post(LLAMA_URL, json={
                "model": LLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": ozet_uzunluk,
                "temperature": 0.3,
            }, timeout=90)
            r_llm.raise_for_status()
            choices = r_llm.json().get("choices", [])
            ozet = ""
            if choices:
                msg = choices[0]["message"]
                ozet = (msg.get("content") or "").strip()
                if not ozet:
                    reasoning = (msg.get("reasoning_content") or "").strip()
                    turkce = [p.strip() for p in reasoning.split("\n")
                              if len(p.strip()) > 30 and any(c in p for c in "şğüöçıŞĞÜÖÇİ")]
                    ozet = "\n".join(turkce[:8]) if turkce else reasoning[:600]

            if not ozet:
                return f"⚠️ Özet üretilemedi.\nHam metin (ilk 500 karakter):\n{metin[:500]}"

            baslik = f"📖 <b>{kaynak[:60]}</b>"
            sonuc = f"{baslik}\n\n{ozet}"

            # Kaydet modunda ChromaDB'ye ekle
            if mod == "kaydet":
                try:
                    col = _get_chroma_col()
                    if col:
                        ts = datetime.datetime.now().isoformat()[:19]
                        doc_id = f"pdf_{ts.replace(':', '').replace('-', '').replace('T', '_')}"
                        col.add(
                            documents=[f"[PDF/WEB] {kaynak_url}\n{ozet}"],
                            ids=[doc_id],
                            metadatas=[{"kaynak": kaynak_url, "tip": "pdf_ozet", "ts": ts}]
                        )
                        sonuc += f"\n\n✅ ChromaDB'ye kaydedildi: <code>{doc_id}</code>"
                except Exception as ce:
                    sonuc += f"\n\n⚠️ Kayıt hatası: {ce}"

            return sonuc
        except Exception as e:
            return f"pdf_reader hatası: {e}"

    elif name == "internet_status":
        return _check_internet()

    elif name == "system_info":
        return _get_system_info(args.get("konu", "hepsi"))

    elif name == "memory_manage":
        islem = args.get("islem", "istatistik")
        sorgu = args.get("sorgu", "")
        try:
            col = _get_chroma_col()
            if col is None:
                return "❌ ChromaDB başlatılamadı."

            if islem == "istatistik":
                total = col.count()
                return (f"📚 <b>ChromaDB Hafıza İstatistiği</b>\n"
                        f"Koleksiyon: {CHROMA_COL}\n"
                        f"Toplam kayıt: {total}\n"
                        f"Durum: ✅ Aktif (in-process)")

            elif islem == "listele":
                n = min(5, col.count())
                if n == 0:
                    return "📭 Henüz kayıt yok."
                result = col.query(query_texts=[sorgu or "genel konuşmalar"], n_results=n)
                docs = result.get("documents", [[]])[0]
                ids  = result.get("ids", [[]])[0]
                if not docs:
                    return "📭 Kayıt bulunamadı."
                lines = ["📋 <b>Hafıza Kayıtları:</b>"]
                for i, (doc, did) in enumerate(zip(docs, ids), 1):
                    lines.append(f"{i}. <code>{did}</code>\n   {str(doc)[:120]}...")
                return "\n".join(lines)

            elif islem == "ara":
                if not sorgu:
                    return "⚠️ Arama için 'sorgu' gerekli."
                n = min(5, col.count())
                if n == 0:
                    return "📭 Henüz kayıt yok."
                result = col.query(query_texts=[sorgu], n_results=n)
                docs  = result.get("documents", [[]])[0]
                ids   = result.get("ids", [[]])[0]
                dists = result.get("distances", [[]])[0]
                if not docs:
                    return f"📭 '{sorgu}' için sonuç bulunamadı."
                lines = [f"🔍 <b>'{sorgu}' sonuçları:</b>"]
                for i, (doc, did, dist) in enumerate(zip(docs, ids, dists), 1):
                    lines.append(f"{i}. [{dist:.3f}] <code>{did}</code>\n   {str(doc)[:150]}")
                return "\n".join(lines)

            elif islem == "sil":
                if not sorgu:
                    return "⚠️ Silmek için kayıt ID'si ('sorgu' alanı) gerekli."
                col.delete(ids=[sorgu])
                return f"🗑️ Kayıt silindi: <code>{sorgu}</code>"

            elif islem == "arsivle":
                if not sorgu:
                    return "⚠️ Arşivlemek için arama sorgusu gerekli."
                n = min(3, col.count())
                if n == 0:
                    return "📭 Arşivlenecek kayıt yok."
                result = col.query(query_texts=[sorgu], n_results=n)
                ids = result.get("ids", [[]])[0]
                if not ids:
                    return f"📭 '{sorgu}' için arşivlenecek kayıt bulunamadı."
                ts = datetime.datetime.now().isoformat()[:19]
                col.update(ids=ids, metadatas=[{"archived": True, "archive_ts": ts}] * len(ids))
                return f"📦 {len(ids)} kayıt arşivlendi: {', '.join(ids)}"

            return f"⚠️ Bilinmeyen işlem: {islem}"
        except Exception as e:
            return f"memory_manage hatası: {e}"

    elif name == "chroma_search":
        sorgu = args.get("sorgu", "")
        n = int(args.get("n_sonuc", 5))
        if not sorgu:
            return "⚠️ Arama sorgusu gerekli."
        try:
            col = _get_chroma_col()
            if col is None:
                return "❌ ChromaDB başlatılamadı."
            total = col.count()
            if total == 0:
                return "📭 Hafızada henüz kayıt yok."
            result = col.query(query_texts=[sorgu], n_results=min(n, total))
            docs  = result.get("documents", [[]])[0]
            ids   = result.get("ids", [[]])[0]
            dists = result.get("distances", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            if not docs:
                return f"📭 '{sorgu}' için sonuç yok."
            lines = [f"🧠 <b>ChromaDB: '{sorgu}'</b>  ({len(docs)} sonuç)"]
            for i, (doc, did, dist, meta) in enumerate(zip(docs, ids, dists, metas), 1):
                arch = " [ARŞİV]" if (meta or {}).get("archived") else ""
                benzerlik = max(0.0, 1.0 - dist)
                lines.append(f"\n{i}. <code>{did}</code>{arch} — {benzerlik:.0%}\n{str(doc)[:200]}")
            return "\n".join(lines)
        except Exception as e:
            return f"chroma_search hatası: {e}"

    elif name == "self_update":
        hedef = args.get("hedef", "")
        deger = args.get("deger", "")
        try:
            if hedef == "oku_persona":
                data = json.loads(PERSONA_PATH.read_text(encoding="utf-8"))
                arketipler = [a.get("isim","?") for a in data.get("arketipler", [])]
                yasaklar = data.get("yasakli_ifadeler", [])[:3]
                return (f"📖 <b>Persona:</b>\n"
                        f"Arketipler: {', '.join(arketipler)}\n"
                        f"Yasaklı ifadeler (ilk 3): {', '.join(yasaklar)}")

            elif hedef == "oku_mood":
                mood_d = json.loads(MOOD_PATH.read_text(encoding="utf-8"))
                duygular = mood_d.get("duygular", {})
                aktif = sorted([(k,v) for k,v in duygular.items() if v > 0.1], key=lambda x: -x[1])
                ilgi = mood_d.get("odul_mekanizmasi", {}).get("ilgi_skoru", 0.5)
                lines = [f"🧠 <b>Mevcut Ruh Hali:</b>  (ilgi_skoru: {ilgi:.2f})"]
                for k, v in aktif:
                    bar = "█" * int(v * 10) + "░" * (10 - int(v * 10))
                    lines.append(f"{k:18s} {bar} {v:.2f}")
                return "\n".join(lines)

            elif hedef == "mood_sifirla":
                mood_d = json.loads(MOOD_PATH.read_text(encoding="utf-8"))
                for k in mood_d.get("duygular", {}):
                    mood_d["duygular"][k] = 0.5 if k == "sogukkan" else 0.3
                mood_d["_son_guncelleme"] = datetime.datetime.now().isoformat()[:19]
                MOOD_PATH.write_text(json.dumps(mood_d, ensure_ascii=False, indent=2), encoding="utf-8")
                return "✅ Ruh hali sıfırlandı — tüm duygular baseline'a çekildi."

            elif hedef == "pc_takvim":
                if not deger:
                    return (f"💻 <b>PC Takvimi:</b>\n"
                            f"Hafta içi: {PC_SCHEDULE['hafta_ici']['acilis']}–{PC_SCHEDULE['hafta_ici']['kapanis']}\n"
                            f"Hafta sonu: {PC_SCHEDULE['hafta_sonu']['acilis']}–{PC_SCHEDULE['hafta_sonu']['kapanis']}\n"
                            f"(Güncelleme için: 'hafta_ici 10:00-02:00' formatında deger ver)")
                # Basit parser: "hafta_ici 10:00-02:00"
                parts = deger.strip().split()
                if len(parts) == 2 and "-" in parts[1]:
                    gun_turu = parts[0]
                    zaman = parts[1].split("-")
                    if gun_turu in PC_SCHEDULE and len(zaman) == 2:
                        PC_SCHEDULE[gun_turu]["acilis"] = zaman[0]
                        PC_SCHEDULE[gun_turu]["kapanis"] = zaman[1]
                        return f"✅ PC takvimi güncellendi: {gun_turu} {zaman[0]}–{zaman[1]}"
                return "⚠️ Format: 'hafta_ici 10:00-02:00' veya 'hafta_sonu 11:00-03:00'"

            elif hedef == "kullanici_tercih":
                if not deger:
                    tercihler = "\n• ".join(KULLANICI_PROFILI["tercihler"])
                    return f"👤 <b>Kullanıcı Tercihleri:</b>\n• {tercihler}"
                KULLANICI_PROFILI["tercihler"].append(deger)
                return f"✅ Yeni tercih eklendi: {deger}"

            return f"⚠️ Bilinmeyen hedef: {hedef}"
        except Exception as e:
            return f"self_update hatası: {e}"

    elif name == "reminder":
        import threading as _thr
        mesaj = args.get("mesaj", "Hatırlatma!")
        dakika = args.get("dakika")
        saat_str = args.get("saat")

        if saat_str:
            # Belirli saatte: "HH:MM"
            try:
                h, m = map(int, saat_str.split(":"))
                now = datetime.datetime.now()
                hedef = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if hedef <= now:
                    hedef += datetime.timedelta(days=1)
                bekleme = int((hedef - now).total_seconds())
                hedef_str = hedef.strftime("%H:%M")
            except Exception:
                return "⚠️ Saat formatı hatalı. Kullanım: 'HH:MM' (ör: '22:00')"
        elif dakika:
            bekleme = int(dakika) * 60
            hedef_str = f"{dakika} dakika sonra"
        else:
            return "⚠️ 'dakika' veya 'saat' parametresi gerekli."

        def _hatirlatici():
            time.sleep(bekleme)
            try:
                send_msg(ALLOWED_ID, f"⏰ <b>Hatırlatma:</b> {mesaj}")
                _log(f"[REMINDER] Gönderildi: {mesaj[:60]}")
            except Exception as e:
                _log(f"[REMINDER] Hata: {e}")

        _thr.Thread(target=_hatirlatici, daemon=True, name="reminder").start()
        return f"⏰ Hatırlatıcı kuruldu — {hedef_str}: <i>{mesaj}</i>"

    elif name == "github":
        islem  = args.get("islem", "durum")
        mesaj  = args.get("mesaj", "")
        icerik = args.get("icerik", "")
        repo   = "KuroShinHQ/KuroShinHQ"
        token  = os.getenv("GITHUB_TOKEN", "")
        git_dir = "/mnt/c/Kuroshin"

        if islem == "durum":
            r = subprocess.run(
                ["bash", "-c", f"cd {git_dir} && GIT_OPTIONAL_LOCKS=0 git status --short && echo '---' && GIT_OPTIONAL_LOCKS=0 git log --oneline -5"],
                capture_output=True, text=True, timeout=60
            )
            return f"📁 <b>Git Durumu — {repo}</b>\n<pre>{r.stdout.strip()}</pre>"

        elif islem in ("push", "push_zorunlu"):
            if not token:
                return "⚠️ GITHUB_TOKEN .env'de ayarlanmamış. Önce token ekleyin."
            commit_msg = mesaj or f"Kuroshin otonom güncelleme — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            force = (islem == "push_zorunlu")
            _PENDING_PUSH["msg"]   = commit_msg
            _PENDING_PUSH["force"] = force
            _PENDING_PUSH["token"] = token
            _PENDING_PUSH["repo"]  = repo
            _PENDING_PUSH["dir"]   = git_dir
            force_txt = " ⚠️ FORCE" if force else ""
            send_msg_keyboard(
                _CURRENT_CHAT_ID,
                f"⚠️ <b>GitHub Push Onayı{force_txt}</b>\n"
                f"Repo: <code>{repo}</code>\n"
                f"Commit: <code>{commit_msg[:80]}</code>\n"
                f"Onaylıyor musunuz?",
                [[{"text": "✅ Onayla", "callback_data": "github_push_onayla"},
                  {"text": "❌ İptal",  "callback_data": "github_push_iptal"}]]
            )
            return "⏳ Push için Telegram onayı bekleniyor."

        elif islem == "issue_ac":
            if not token:
                return "⚠️ GITHUB_TOKEN .env'de ayarlanmamış."
            if not mesaj:
                return "⚠️ Issue başlığı (mesaj) gerekli."
            import json as _json
            payload = _json.dumps({"title": mesaj, "body": icerik or mesaj})
            r = subprocess.run(
                ["bash", "-c",
                 f"curl -s -X POST -H 'Authorization: token {token}' "
                 f"-H 'Content-Type: application/json' "
                 f"-d '{payload}' "
                 f"https://api.github.com/repos/{repo}/issues"],
                capture_output=True, text=True, timeout=30
            )
            try:
                resp = json.loads(r.stdout)
                url  = resp.get("html_url", "?")
                num  = resp.get("number", "?")
                aktivite_kaydet(f"GitHub issue açıldı #{num}: {mesaj[:60]}", detay=icerik[:100], kategori="github")
                return f"✅ Issue açıldı: <a href='{url}'>#{num} — {mesaj[:60]}</a>"
            except Exception:
                return f"❌ Issue hatası: {r.stdout[:300]}"

        elif islem == "issue_listele":
            if not token:
                return "⚠️ GITHUB_TOKEN .env'de ayarlanmamış."
            r = subprocess.run(
                ["bash", "-c",
                 f"curl -s -H 'Authorization: token {token}' "
                 f"https://api.github.com/repos/{repo}/issues?state=open&per_page=10"],
                capture_output=True, text=True, timeout=30
            )
            try:
                issues = json.loads(r.stdout)
                if not issues:
                    return "ℹ️ Açık issue yok."
                lines = [f"📋 <b>Açık Issues — {repo}</b>"]
                for iss in issues[:10]:
                    lines.append(f"  #{iss['number']} {iss['title'][:60]}")
                return "\n".join(lines)
            except Exception:
                return f"❌ Issue listesi hatası: {r.stdout[:300]}"

        elif islem == "son_commitler":
            r = subprocess.run(
                ["bash", "-c", f"cd {git_dir} && GIT_OPTIONAL_LOCKS=0 git log --oneline -10"],
                capture_output=True, text=True, timeout=60
            )
            return f"📜 <b>Son 10 Commit</b>\n<pre>{r.stdout.strip()}</pre>"

        return f"⚠️ Bilinmeyen GitHub işlemi: {islem}"

    elif name == "gemini":
        # google-genai (yeni paket) veya google-generativeai (eski) ile çalış
        _gnai_client = None
        _gnai_legacy = None
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return "⚠️ GEMINI_API_KEY .env'de ayarlanmamış."
        try:
            from google import genai as _gnai_new
            _gnai_client = _gnai_new.Client(api_key=api_key)
        except Exception:
            try:
                import google.generativeai as _gnai_old
                _gnai_old.configure(api_key=api_key)
                _gnai_legacy = _gnai_old
            except ImportError:
                return "❌ google-genai kurulu değil. Kurun: pip install google-genai"

        islem       = args.get("islem", "sor")
        soru        = args.get("soru", "")
        kendi_yanit = args.get("kendi_yanitim", "")

        if not soru:
            return "⚠️ 'soru' parametresi gerekli."

        if islem == "sor":
            prompt = soru
        elif islem == "tartis":
            prompt = (
                f"Aşağıdaki konuda eleştirel ve farklı bir bakış açısı sun. "
                f"Karşı argümanlar, göz ardı edilen riskler veya alternatif perspektifler ver. "
                f"Kısa ve odaklı ol (max 300 kelime).\n\nKonu: {soru}"
            )
        elif islem == "karsilastir":
            prompt = (
                f"Soru: {soru}\n\n"
                f"Bir AI'ın verdiği yanıt: {kendi_yanit}\n\n"
                f"Bu yanıtı değerlendir — doğru mu, eksik ne var, ne eklersin? "
                f"Kısa tut (max 200 kelime)."
            )
        else:
            prompt = soru

        try:
            if _gnai_client:
                response = _gnai_client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt
                )
            else:
                _model = _gnai_legacy.GenerativeModel("gemini-2.0-flash")
                response = _model.generate_content(prompt)
            yanit = response.text.strip()
            prefix = {
                "sor":         "🤖 Gemini",
                "tartis":      "🤖 Gemini (karşı görüş)",
                "karsilastir": "🤖 Gemini (değerlendirme)",
            }
            _log(f"[GEMINI] {islem} | {len(yanit)} kar")
            aktivite_kaydet(f"Gemini {islem}: {soru[:80]}", detay=yanit[:100], kategori="gemini")
            return f"{prefix.get(islem, '🤖 Gemini')}:\n{yanit[:1500]}"

        except Exception as e:
            err = str(e)
            _log(f"[GEMINI] Hata: {err[:200]}")
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                return "⚠️ Gemini günlük kota doldu — gece yarısı UTC'de sıfırlanır."
            if "404" in err or "NOT_FOUND" in err:
                return "⚠️ Gemini model bulunamadı — model adı güncellenmeli."
            return f"❌ Gemini hatası: {err[:200]}"

    elif name == "aktivite_gunluk":
        islem    = args.get("islem", "listele")
        eylem    = args.get("eylem", "")
        kategori = args.get("kategori", "genel")
        bugun    = datetime.datetime.now().date().isoformat()
        log_file = AKTIVITE_LOG_DIR / f"{bugun}.md"

        if islem == "listele":
            if not log_file.exists():
                return f"📓 Bugün ({bugun}) henüz aktivite kaydı yok."
            icerik = log_file.read_text(encoding="utf-8")
            satirlar = [l for l in icerik.split('\n') if l.startswith('- [')]
            if not satirlar:
                return "📓 Bugün kayıtlı aktivite yok."
            return (f"📓 <b>Aktivite Günlüğü — {bugun}</b>\n"
                    + "\n".join(satirlar[:20]))

        elif islem == "ozet":
            if not log_file.exists():
                return f"📓 Bugün ({bugun}) henüz aktivite kaydı yok."
            icerik = log_file.read_text(encoding="utf-8")
            try:
                r = requests.post(LLAMA_URL, json={
                    "model": LLAMA_MODEL,
                    "messages": [{"role": "user", "content":
                        "SADECE TÜRKÇE YAZ.\n"
                        f"Sen Kuroshin'sin. Bugünkü aktivite günlüğün:\n{icerik[:2000]}\n\n"
                        "Bu günü 3-4 cümleyle özetle. 'Bugün şunları yaptım:' ile başla."}],
                    "max_tokens": 300, "temperature": 0.4,
                }, timeout=60)
                r.raise_for_status()
                ozet = _strip_think((r.json()["choices"][0]["message"].get("content") or "").strip())
                return f"📓 <b>Günlük Özet — {bugun}</b>\n{ozet}" if ozet else "⚠️ Özet üretilemedi."
            except Exception as e:
                return f"❌ Özet hatası: {e}"

        elif islem == "kaydet":
            if not eylem:
                return "⚠️ 'eylem' parametresi gerekli."
            aktivite_kaydet(eylem, kategori=kategori)
            return f"✅ Aktivite kaydedildi: [{kategori}] {eylem}"

        return f"⚠️ Bilinmeyen işlem: {islem}"

    return f"Bilinmeyen araç: {name}"

# ── TELEGRAM INLINE KEYBOARD ──────────────────────────
def send_msg_keyboard(chat_id: int, text: str, keyboard: list):
    try:
        r = requests.post(f"{TELEGRAM_URL}/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": keyboard}
        }, timeout=10)
        resp = r.json()
        if resp.get("ok"):
            _log(f"[KEYBOARD] Gönderildi ✅ (msg_id={resp['result']['message_id']})")
        else:
            _log(f"[KEYBOARD] Telegram hatası: {resp.get('description', resp)}")
    except Exception as e:
        _log(f"[KEYBOARD] Gönderim hatası: {e}")

def answer_callback(callback_id: str, text: str = ""):
    try:
        requests.post(f"{TELEGRAM_URL}/answerCallbackQuery", json={
            "callback_query_id": callback_id, "text": text
        }, timeout=5)
    except Exception:
        pass

# ── İLGİ PROFİLİ ÖĞRENİMİ ────────────────────────────
def _feedback_isle(konu: str, puan: str):
    """Gelen feedback'i ilgi_profili.json'a kaydet ve mood'a yansıt. puan: 'iyi' | 'kotu' | 'daha'"""
    try:
        profil = json.loads(ILGI_PROFILI_PATH.read_text(encoding="utf-8"))
        if puan == "iyi":
            guclu = profil.setdefault("guclu_tepki_verilen", [])
            if konu not in guclu:
                guclu.insert(0, konu)
                guclu[:] = guclu[:10]
        elif puan == "kotu":
            zayif = profil.setdefault("zayif_tepki_verilen", [])
            if konu not in zayif:
                zayif.append(konu)
            guclu = profil.get("guclu_tepki_verilen", [])
            if konu in guclu:
                guclu.remove(konu)
        profil["son_paylasilan_konu"] = konu
        profil["toplam_paylasim"] = profil.get("toplam_paylasim", 0) + 1
        ILGI_PROFILI_PATH.write_text(json.dumps(profil, ensure_ascii=False, indent=2), encoding="utf-8")
        _log(f"[FEEDBACK] {konu} → {puan}")
    except Exception as e:
        _log(f"[FEEDBACK] İşleme hatası: {e}")

    # Mood'a kalıcı yansıt
    _MOOD_DELTA = {
        "iyi":  {"heyecan": +0.12, "merak": +0.08, "gurur": +0.10},
        "kotu": {"tatminsizlik": +0.10, "huzun": +0.05},
        "daha": {"merak": +0.20, "heyecan": +0.08},
    }
    delta = _MOOD_DELTA.get(puan, {})
    if delta:
        try:
            _, mood = _load_soul()
            mood = _apply_mood_delta(mood, delta)
            _save_mood(mood)
            _log(f"[FEEDBACK] Mood güncellendi: {delta}")
        except Exception as e:
            _log(f"[FEEDBACK] Mood güncelleme hatası: {e}")

def _feedback_kaydet_json(konu: str, puan: str):
    """Detaylı feedback.json'a da kaydet."""
    try:
        fb_path = Path("/mnt/c/Kuroshin/memory/feedback.json")
        fb = json.loads(fb_path.read_text(encoding="utf-8")) if fb_path.exists() else []
        fb.append({"ts": datetime.datetime.now().isoformat()[:19], "konu": konu, "puan": puan})
        fb_path.write_text(json.dumps(fb[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

# ── RÜYA TAM YORUM ────────────────────────────────────
def _get_dream_yorum() -> str:
    """Dream Engine rüyasını model ile yorumla, tam metin döndür."""
    try:
        if not LAST_DREAM_FILE.exists():
            return ""
        data = json.loads(LAST_DREAM_FILE.read_text(encoding="utf-8"))
        preview = data.get("preview", "").strip()
        tarih   = data.get("date", "")
        if not preview:
            return ""
        bugun = datetime.datetime.now().date().isoformat()
        dun   = (datetime.datetime.now().date() - datetime.timedelta(days=1)).isoformat()
        if tarih not in (bugun, dun):
            return ""
        yorum_prompt = (
            f"SADECE TÜRKÇE YAZ.\n"
            f"Sen Kuroshin'sin. Dün gece bu rüyayı gördün:\n\"{preview[:400]}\"\n\n"
            f"Bu rüya sende ne hissettiriyor? 2-3 cümle, içten, kişisel. "
            f"'Lordum, bu gece ...' ile başla."
        )
        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": yorum_prompt}],
            "max_tokens": 250, "temperature": 0.75, "repeat_penalty": 1.3,
        }, timeout=60)
        r.raise_for_status()
        raw = (r.json()["choices"][0]["message"].get("content") or "").strip()
        temiz = _strip_think(raw).strip('"').strip("'").strip()
        return temiz
    except Exception as e:
        _log(f"[RUYA] Yorum hatası: {e}")
        return ""

# ── GÜNLÜK KEŞİF ÖZETİ ────────────────────────────────
_CANLILIK_SORGULAR = [
    "AI model consciousness experiments 2026",
    "autonomous LLM behavior emergent personality",
    "LLM intrinsic motivation self-awareness research",
    "character AI persona persistence architecture",
    "emotional AI state machine design patterns",
]

def _canlilik_arastir():
    """Her 7 günde bir: yapay zeka canlılık şemalarını araştır, keşifleri kaydet."""
    import random
    sorgu = random.choice(_CANLILIK_SORGULAR)
    _log(f"[CANLILIK] Araştırma başladı: {sorgu}")
    try:
        sonuc = run_tool("walker_research", {"task": sorgu})
        if not sonuc or len(sonuc) < 60 or "❌" in sonuc:
            sonuc = run_tool("web_search", {"task": sorgu})
        if not sonuc or len(sonuc) < 60:
            _log("[CANLILIK] Sonuç yetersiz, atlandı.")
            return

        # logs/schema_kesfler/ dosyasına yaz
        kesfler_dir = Path("/mnt/c/Kuroshin/logs/schema_kesfler")
        kesfler_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        dosya = kesfler_dir / f"canlilik_{ts}.md"
        dosya.write_text(
            f"# Canlılık Araştırması — {datetime.datetime.now().strftime('%Y-%m-%d')}\n"
            f"**Sorgu:** {sorgu}\n\n{sonuc[:1500]}\n",
            encoding="utf-8"
        )

        # schema_onerileri.json güncelle
        schema_path = Path("/mnt/c/Kuroshin/memory/schema_onerileri.json")
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else []
            if not isinstance(schema, list):
                schema = []
            schema.append({"ts": datetime.datetime.now().isoformat()[:19], "sorgu": sorgu, "ozet": sonuc[:300]})
            schema_path.write_text(json.dumps(schema[-20:], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        # LLM ile Kuroshin'e uyarlanabilir kısmı çıkart
        ozet_prompt = (
            "SADECE TÜRKÇE YAZ.\n"
            f"Araştırma: '{sorgu}'\nBulgu:\n{sonuc[:600]}\n\n"
            "Bu bulguda Kuroshin'e uygulanabilecek en ilginç 1 fikri 2 cümleyle özetle. "
            "'Bu araştırmada şunu keşfettim: ...' ile başla."
        )
        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": ozet_prompt}],
            "max_tokens": 400, "temperature": 0.7,
        }, timeout=90)
        r.raise_for_status()
        ozet = (r.json()["choices"][0]["message"].get("content") or "").strip()
        # 35B model uzun cümle üretirse, son tam cümlede kes
        import re as _re_ozet
        ozet_clean = _re_ozet.sub(r"<think>.*?</think>", "", ozet, flags=_re_ozet.DOTALL).strip()
        son_nokta = max(ozet_clean.rfind("."), ozet_clean.rfind("!"), ozet_clean.rfind("?"))
        if son_nokta > 30:
            ozet_clean = ozet_clean[:son_nokta + 1]
        if ozet_clean and len(ozet_clean) > 20:
            send_msg(ALLOWED_ID, f"🧬 <b>Canlılık Keşfi</b>\n\n{ozet_clean}")
            _save_to_chroma(f"[CANLILIK] {sorgu}", ozet)
        _log(f"[CANLILIK] Tamamlandı → {dosya.name}")
    except Exception as e:
        _log(f"[CANLILIK] Hata: {e}")


def _chroma_prune(col, ids: list, metas: list, total: int):
    """ChromaDB CHROMA_PRUNE_THRESHOLD'u geçince eski kayıtları sil (ts metadata'ya göre)."""
    try:
        n_delete = total - CHROMA_PRUNE_KEEP_LAST
        if n_delete <= 0:
            return
        zipped = list(zip(ids, metas or [{}] * len(ids)))
        zipped.sort(key=lambda x: int(x[1].get("ts", "0")))
        to_delete = [id_ for id_, _ in zipped[:n_delete]]
        if to_delete:
            col.delete(ids=to_delete)
            _log(f"[CHROMA] Prune: {len(to_delete)} eski kayıt silindi. Kalan: {col.count()}")
    except Exception as e:
        _log(f"[CHROMA] Prune hatası: {e}")


def _chroma_haftalik_ozet():
    """Her Pazar 23:00 polling loop'tan tetiklenir. Özetler, arşivler, CHROMA_PRUNE_THRESHOLD
    geçilmişse eski kayıtları temizler."""
    try:
        col = _get_chroma_col()
        if col is None or col.count() < 20:
            return
        sonuclar = col.get(include=["documents", "metadatas"])
        docs  = sonuclar.get("documents", [])
        ids   = sonuclar.get("ids", [])
        metas = sonuclar.get("metadatas", [])
        if not docs:
            return
        ozet_prompt = (
            "SADECE TÜRKÇE YAZ.\n"
            f"Bu hafta Kuroshin hafızasında {len(docs)} kayıt var.\n"
            f"İlk 10 kayıt: {chr(10).join(docs[:10])[:800]}\n\n"
            "Bu haftanın en önemli 3 konusunu ve öğrenilen şeyleri 3-4 cümleyle özetle. "
            "'Bu hafta şunları öğrendim: ...' ile başla."
        )
        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": ozet_prompt}],
            "max_tokens": 300, "temperature": 0.6,
        }, timeout=90)
        r.raise_for_status()
        ozet = (r.json()["choices"][0]["message"].get("content") or "").strip()
        if ozet and len(ozet) > 20:
            hafta = datetime.datetime.now().strftime("%Y-W%W")
            arsiv = Path(f"/mnt/c/Kuroshin/memory/arsiv/chroma_{hafta}.md")
            arsiv.parent.mkdir(parents=True, exist_ok=True)
            arsiv.write_text(f"# ChromaDB Özet — {hafta}\n\n{ozet}\n\nKayıt sayısı: {len(docs)}\n",
                             encoding="utf-8")
            send_msg(ALLOWED_ID, f"📚 <b>Haftalık Hafıza Özeti</b>\n\n{ozet}")
            _log(f"[CHROMA] Haftalık özet oluşturuldu: {hafta} ({len(docs)} kayıt)")
        # Prune: eşik aşıldıysa eski kayıtları sil
        if len(ids) > CHROMA_PRUNE_THRESHOLD:
            _chroma_prune(col, ids, metas, len(ids))
    except Exception as e:
        _log(f"[CHROMA] Haftalık özet hatası: {e}")

def _gunluk_kesif_ozeti():
    """Gece 22:00 — bugünkü probe araştırmalarını özetle ve gönder."""
    try:
        col = _get_chroma_col()
        if col is None or col.count() == 0:
            return
        bugun = datetime.datetime.now().date().isoformat()
        sonuclar = col.get()
        bugun_docs = [
            d for d in (sonuclar.get("documents") or [])
            if d and bugun in d and "[PROBE" in d
        ]
        # Tek kayıt varsa sadece özet yapmaya değmez — probe mesajı zaten gitti
        if len(bugun_docs) < 2:
            _log("[OZET] Bugün yeterli probe kaydı yok (min 2), özet atlandı.")
            return
        ozet_input = "\n---\n".join(d[:300] for d in bugun_docs[:5])
        ozet_prompt = (
            "SADECE TÜRKÇE YAZ. Aşağıdaki talimatı tekrar etme, doğrudan cevabı yaz.\n"
            f"Sen Kuroshin'sin. Bugün şu konuları araştırdın:\n{ozet_input}\n\n"
            "Yukarıdaki araştırmaları sentezleyerek 3 cümlelik özgün bir özet yaz. "
            "'Lordum, bugün ...' ile başla. Sadece özeti yaz, talimatı tekrarlama."
        )
        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": ozet_prompt}],
            "max_tokens": 250, "temperature": 0.6, "repeat_penalty": 1.3,
        }, timeout=90)
        r.raise_for_status()
        ozet = (r.json()["choices"][0]["message"].get("content") or "").strip()
        # Prompt leak kontrolü — instrüksiyon cümlesi cevaba sızdıysa temizle
        _LEAK_PREFIXLER = ["Günü 3-4 cümleyle", "Aşağıdaki talimatı", "SADECE TÜRKÇE"]
        for leak in _LEAK_PREFIXLER:
            if ozet.startswith(leak):
                idx = ozet.find("Lordum")
                ozet = ozet[idx:] if idx != -1 else ""
        if ozet and len(ozet) > 20:
            send_msg(ALLOWED_ID, f"🌙 <b>Günlük Keşif Özeti</b>\n\n{ozet}")
            _log("[OZET] Günlük keşif özeti gönderildi.")
    except Exception as e:
        _log(f"[OZET] Hata: {e}")

# ── MERAK LİSTESİ ──────────────────────────────────────
MERAK_COL = "merak_listesi"

def _merak_ekle(soru: str):
    """Araştırmadan doğan yeni merak sorusunu ChromaDB merak_listesi'ne ekle."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        col = client.get_or_create_collection(MERAK_COL)
        ts = datetime.datetime.now().isoformat()[:19]
        doc_id = f"merak_{ts.replace(':', '').replace('-', '').replace('T', '_')}"
        col.add(documents=[f"[{ts}] {soru}"], ids=[doc_id])
        _log(f"[MERAK] Eklendi: {soru[:60]}")
    except Exception as e:
        _log(f"[MERAK] Eklenemedi: {e}")

def _merak_listeden_konu() -> str:
    """merak_listesi koleksiyonundan bir konu çek, yoksa ilgi_profili'ne dön."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        col = client.get_or_create_collection(MERAK_COL)
        if col.count() == 0:
            return ""
        sonuclar = col.get()
        docs = sonuclar.get("documents") or []
        ids  = sonuclar.get("ids") or []
        if docs:
            # En eski soruyu al (FIFO)
            konu = docs[0].split("] ", 1)[-1][:80] if "] " in docs[0] else docs[0][:80]
            # Kullandıktan sonra sil
            try:
                col.delete(ids=[ids[0]])
            except Exception:
                pass
            # Soru cümlesi veya çok uzunsa geçersiz konu — atla, ilgi_profili'ne dön
            if "?" in konu or len(konu.split()) > 7:
                _log(f"[MERAK] Geçersiz konu atlandı ({len(konu.split())} kelime): {konu[:60]}")
                return ""
            return konu
    except Exception:
        pass
    return ""

# ── DENEYİM GÜNLÜĞÜ ───────────────────────────────────
DENEYIM_DIR = Path("/mnt/c/Kuroshin/logs/deneyimler")

def _deneyim_kaydet(konu: str, icerik: str):
    try:
        DENEYIM_DIR.mkdir(parents=True, exist_ok=True)
        tarih = datetime.datetime.now().strftime("%Y-%m-%d")
        dosya = DENEYIM_DIR / f"{tarih}.md"
        ts    = datetime.datetime.now().strftime("%H:%M")
        with dosya.open("a", encoding="utf-8") as f:
            f.write(f"\n## [{ts}] {konu}\n{icerik}\n")
        _log(f"[DENEYIM] Kaydedildi: {konu[:40]}")
    except Exception as e:
        _log(f"[DENEYIM] Kayıt hatası: {e}")

# ── OODA IDLE PROBE ───────────────────────────────────
IDLE_PROBE_ARALIK = 7200  # saniye — 2 saatte bir tetikle
_son_probe_ts: float = 0.0
ILGI_PROFILI_PATH = Path("/mnt/c/Kuroshin/memory/ilgi_profili.json")

def _konu_sec() -> str:
    """Merak listesi → ilgi profili yenilik skoru sırasıyla konu seç."""
    # Önce merak listesinden bak
    merak = _merak_listeden_konu()
    if merak:
        return merak
    try:
        profil = json.loads(ILGI_PROFILI_PATH.read_text(encoding="utf-8"))
        alanlar  = profil.get("ilgi_alanlari", ["yapay zeka", "felsefe", "siber güvenlik"])
        guclu    = profil.get("guclu_tepki_verilen", [])
        zayif    = profil.get("zayif_tepki_verilen", [])
        sayaclar = profil.get("arastirilan_konular", {})
        # Zayıf tepki verilenleri çıkar
        kandidatlar = list(dict.fromkeys(guclu + alanlar))
        kandidatlar = [k for k in kandidatlar if k not in zayif]
        kandidatlar.sort(key=lambda k: sayaclar.get(k, 0))
        return kandidatlar[0] if kandidatlar else "yapay zeka"
    except Exception:
        return "felsefe"

def _yenilik_sayac_artir(konu: str):
    try:
        profil = json.loads(ILGI_PROFILI_PATH.read_text(encoding="utf-8"))
        sayaclar = profil.setdefault("arastirilan_konular", {})
        sayaclar[konu] = sayaclar.get(konu, 0) + 1
        ILGI_PROFILI_PATH.write_text(json.dumps(profil, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _sessizlik_dk() -> float:
    """Son etkileşimden bu yana geçen dakika."""
    try:
        _, mood = _load_soul()
        son_str = mood.get("iliskisel_sayac", {}).get("son_etkilesim_zamani", "")
        if not son_str:
            return 999.0
        return (datetime.datetime.now() - datetime.datetime.fromisoformat(son_str)).total_seconds() / 60.0
    except Exception:
        return 999.0

def _ooda_karar(mood: dict, sessizlik: float, kalan: int) -> str:
    """Orient + Decide: ne yapmalı?"""
    if kalan <= 0:
        return "dur"
    if sessizlik < 30:
        return "dur"
    duygular  = mood.get("duygular", {})
    merak     = duygular.get("merak", 0.5)
    yorgunluk = duygular.get("yorgunluk", 0.0)
    if yorgunluk > 0.75 and kalan <= 1:
        return "dusun"
    # Çok uzun sessizlik (6+ saat) → ilgisizlik reaksiyonu
    if sessizlik >= 360:
        return "ilgisizlik"
    if merak > 0.55 or sessizlik >= 120:
        return "arastir"
    return "paylasim"

def _idle_probe(zorla: bool = False):
    """OODA heartbeat — arka plan thread'den çağrılır."""
    global _son_probe_ts
    _son_probe_ts = time.time()

    persona, mood = _load_soul()
    mood = _apply_decay(mood)
    _save_mood(mood)
    sessizlik = _sessizlik_dk()
    kalan = _energy_kalan()
    karar = _ooda_karar(mood, sessizlik if not zorla else 120, kalan)

    _log(f"[PROBE] karar={karar} sessizlik={sessizlik:.0f}dk enerji={kalan}/5")

    if karar == "dur":
        return

    emote = _get_emote(mood)

    if karar == "arastir":
        if not _energy_harca(1):
            _log("[PROBE] Enerji bitti.")
            return
        konu = _konu_sec()
        _yenilik_sayac_artir(konu)
        _log(f"[PROBE] Araştırma: {konu}")

        # Walker'ı 30s'de kesilecek şekilde çalıştır — 180s varsayılan çok uzun
        import concurrent.futures as _cf
        sonuc = ""
        try:
            with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                _fut = _ex.submit(run_tool, "walker_research", {"task": f"{konu} 2026 yeni gelişmeler"})
                sonuc = _fut.result(timeout=30)
        except _cf.TimeoutError:
            _log("[PROBE] Walker 30s'de yanıt vermedi, web_search'e geçiliyor.")
        except Exception as _we:
            _log(f"[PROBE] Walker hata: {_we}")
        if not sonuc or len(sonuc) < 60 or "kapalı" in sonuc or "❌" in sonuc:
            _log(f"[PROBE] web_search fallback (walker: {sonuc[:40]!r})")
            sonuc = run_tool("web_search", {"task": f"{konu} 2026 yeni gelişmeler"})
        if not sonuc or len(sonuc) < 60 or "kapalı" in sonuc or "❌" in sonuc:
            _log("[PROBE] Araştırma servisleri kapalı, merak notu yazılıyor.")
            _deneyim_kaydet(konu, f"Araştırma yapılamadı — servis kapalı. Konu: {konu}")
            _merak_ekle(f"{konu} araştırılacak (servis açılınca)")
            return

        ozet_prompt = (
            f"SADECE TÜRKÇE YAZ. İngilizce kesinlikle kullanma.\n"
            f"Sen Kuroshin'sin. Kendi isteğinle '{konu}' üzerine araştırma yaptın.\n"
            f"Bulduğun şey:\n{sonuc[:700]}\n\n"
            f"Bunu kuroshin_user'ya 2-3 cümleyle, merakını yansıtarak anlat. "
            f"'Lordum, ...' ile başla. Kuru özet değil, senin bakış açın.\n"
            f"Son cümlede bu konudan doğan bir soru sor (merak listesi için)."
        )
        try:
            r = requests.post(LLAMA_URL, json={
                "model": LLAMA_MODEL,
                "messages": [{"role": "user", "content": ozet_prompt}],
                "max_tokens": 350, "temperature": 0.7, "repeat_penalty": 1.3,
            }, timeout=90)
            r.raise_for_status()
            icerik = _strip_think((r.json()["choices"][0]["message"].get("content") or "").strip())
            if icerik and len(icerik) > 20:
                # Inline keyboard ile gönder
                keyboard = [[
                    {"text": "👍 İlginç", "callback_data": f"fb_iyi_{konu[:30]}"},
                    {"text": "👎 Sıkıcı", "callback_data": f"fb_kotu_{konu[:30]}"},
                    {"text": "🔍 Devam araştır", "callback_data": f"fb_daha_{konu[:30]}"},
                ]]
                _log(f"[PROBE] LLM özet hazır ({len(icerik)} kar), Telegram'a gönderiliyor...")
                send_msg_keyboard(ALLOWED_ID, f"{emote} {icerik}", keyboard)
                _save_to_chroma(f"[PROBE-ARASTIRMA] {konu}", icerik)
                _deneyim_kaydet(konu, icerik)
                # Son soruyu merak listesine ekle — kısa (≤6 kelime), soru tümcesi
                satirlar = [s.strip() for s in icerik.split(".") if "?" in s]
                for s in reversed(satirlar):
                    kelimeler = s.split()
                    if 2 <= len(kelimeler) <= 6 and not s.startswith("Bu durumu") and not s.startswith("Sizce"):
                        _merak_ekle(s)
                        break
        except Exception as e:
            _log(f"[PROBE] Özet hatası: {e}")

    elif karar == "paylasim":
        ctx = _get_chroma_context(_konu_sec())
        if not ctx:
            return
        paylasim_prompt = (
            f"SADECE TÜRKÇE YAZ.\n"
            f"Sen Kuroshin'sin, ruh halin: {_mood_summary(mood)}.\n"
            f"Hafızandan bir şey aklına geldi:\n{ctx[:400]}\n\n"
            f"Bunu kuroshin_user'ya düşünceli şekilde paylaş. 1-2 cümle. 'Lordum, ...' ile başla."
        )
        try:
            r = requests.post(LLAMA_URL, json={
                "model": LLAMA_MODEL,
                "messages": [{"role": "user", "content": paylasim_prompt}],
                "max_tokens": 200, "temperature": 0.7, "repeat_penalty": 1.3,
            }, timeout=60)
            r.raise_for_status()
            icerik = _strip_think((r.json()["choices"][0]["message"].get("content") or "").strip())
            if icerik and len(icerik) > 20:
                send_msg(ALLOWED_ID, f"{emote} {icerik}")
        except Exception as e:
            _log(f"[PROBE] Paylaşım hatası: {e}")

    elif karar == "ilgisizlik":
        # 6+ saat sessizlik → strateji değiştir, kullanıcıya sor
        profil = json.loads(ILGI_PROFILI_PATH.read_text(encoding="utf-8")) if ILGI_PROFILI_PATH.exists() else {}
        son_konu = profil.get("son_paylasilan_konu", "")
        # Few-shot + paragraph truncation — test edilmiş %100 geçer
        _d  = f"{sessizlik:.0f}"
        _sk = son_konu[:40] if son_konu else "yok"
        icerik = ""
        try:
            r = requests.post(LLAMA_URL, json={
                "model": LLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": (
                        "Sen Kuroshin'sin: soğuk, analitik. "
                        "Yanıtların 'Lordum,' ile başlar, 1-2 cümle, yalnızca Türkçe."
                    )},
                    {"role": "user",      "content": "120 dakika sessizlik. Son konu: kuantum."},
                    {"role": "assistant", "content": "Lordum, iki saattir sessizsiniz. Kuantum konusuna tepki gelmedi."},
                    {"role": "user",      "content": "720 dakika sessizlik. Son konu: yok."},
                    {"role": "assistant", "content": "Lordum, on iki saattir yanıt yok. Bekliyorum."},
                    {"role": "user",      "content": "2880 dakika sessizlik. Son konu: yok."},
                    {"role": "assistant", "content": "Lordum, iki gündür sessizlik var. Sistemler çalışıyor."},
                    {"role": "user",      "content": f"{_d} dakika sessizlik. Son konu: {_sk}."},
                ],
                "max_tokens": 600, "temperature": 0.4, "repeat_penalty": 1.3,
            }, timeout=60)
            r.raise_for_status()
            raw_ilg = (r.json()["choices"][0]["message"].get("content") or "").strip()
            icerik  = _ilg_post_process(raw_ilg)
        except Exception as e:
            _log(f"[PROBE] İlgisizlik LLM hatası: {e}")

        if not _ilg_validate(icerik):
            _log(f"[PROBE] İlgisizlik dejenere — ham: {icerik[:120]!r}")
            icerik = _random.choice(_ILG_FALLBACK).format(d=sessizlik)
            _log(f"[PROBE] İlgisizlik fallback kullanıldı.")

        send_msg(ALLOWED_ID, f"{emote} {icerik}")
        _log(f"[PROBE] İlgisizlik reaksiyonu gönderildi: {icerik[:60]}")
        # Zayıf tepki — mevcut son konu zayıf listeye
        if son_konu:
            _feedback_isle(son_konu, "kotu")

    elif karar == "dusun":
        ic_ses, _ = _think_turn("Sessizce düşünüyorum.", persona, mood)
        if ic_ses:
            _log_ic_ses(f"[IDLE] {ic_ses}")

# ── SOHBET SORUSU TESPİTİ ─────────────────────────────
_SOHBET_KALIPLARI = [
    "hayalin", "hayali", "hayal", "rüya", "rüyan", "rüya gördün",
    "hissediyorsun", "nasılsın", "ne düşünüyorsun",
    "ne hissediyorsun", "üzgün müsün", "mutlu musun", "seviyor musun",
    "kendini nasıl", "varoluş", "kim olduğun", "ne olduğun",
    "seviyorum", "seni anlat", "kendinden bahset",
    # Selamlama / günün saati — araç gerektirmez
    "günaydın", "iyi geceler", "gece nasıl", "nasıldı gece",
    "sabah nasıl", "akşam nasıl", "gece nasıldı",
]

def _is_conversational(text: str) -> bool:
    """Felsefi/kişisel/duygusal soru mu? Evet ise araç kullanılmaz."""
    t = text.lower()
    return any(k in t for k in _SOHBET_KALIPLARI)

# ── GEMMA4 ÇAĞRISI ────────────────────────────────────
def call_qwen(messages: list, kullan_arac: bool = True) -> dict:
    payload = {
        "model": LLAMA_MODEL,
        "messages": messages,
        "max_tokens": 1536 if kullan_arac else 512,  # sohbette kısa, araçta tam
        "temperature": 0.4,
        "repeat_penalty": 1.5,
        "frequency_penalty": 0.5,
    }
    if kullan_arac:
        payload["tools"] = TOOLS
    r = requests.post(LLAMA_URL, json=payload, timeout=180)
    r.raise_for_status()
    return r.json()

# ── ANA İŞLEM ─────────────────────────────────────────
def process_message(chat_id: int, text: str, test_mode: bool = False):
    global _CURRENT_CHAT_ID
    _CURRENT_CHAT_ID = chat_id
    _log(f"[CHANCELLOR] Mesaj: {text[:100]}{' [TEST]' if test_mode else ''}")

    # Her mesajda ilgi_skoru güncelle (slash komutları dahil)
    try:
        _persona, _mood = _load_soul()
        _mood = _apply_decay(_mood)
        _mood = _update_ilgi_sayaci(_mood, mesaj_var=True)
        _save_mood(_mood)
    except Exception as _e:
        _log(f"[SOUL] ilgi_skoru güncelleme hatası: {_e}")

    # Slash komutları
    if text in ("/start", "/help", "!help"):
        send_msg(chat_id, (
            "⚔️ <b>Şansölye Komuta Merkezi v2.2</b>\n\n"
            "<b>Sistem Komutları:</b>\n"
            "/status — Servis durumu + VRAM\n"
            "/scan — Hype Scanner manuel tetik\n"
            "/report — Son hype raporu\n\n"
            "<b>Model Yönetimi:</b>\n"
            "/model_list — Mevcut modelleri listele\n"
            "/model_status — Aktif model + hız istatistiği\n"
            "/model_switch &lt;isim&gt; — Modeli değiştir (ör: /model_switch Qwen)\n\n"
            "<b>Sistem Kontrolü:</b>\n"
            "/bat — Bat kontrol paneli\n"
            "/bat_stop — Tüm servisleri kapat\n"
            "/bat_restart — Yeniden başlatma kılavuzu\n\n"
            "<b>İnternet Kontrol:</b>\n"
            "/kota — Kullanım ve limit durumu\n"
            "/limit &lt;GB&gt; — Günlük limiti ayarla\n"
            "/duraklat / /devam — Otonom indirmeleri durdur/başlat\n\n"
            "<b>Otonom Entegrasyon:</b>\n"
            "/bekleyen — Onay bekleyen öğeler\n"
            "/onay_indir &lt;id&gt; — Modeli indir ve test et\n"
            "/onay &lt;id&gt; — Testi geçmiş modeli sisteme ekle\n"
            "/red &lt;id&gt; — Modeli reddet/arşivle\n\n"
            "<b>Görev Çalıştır:</b>\n"
            "/cron &lt;bash komutu&gt; — Anlık cron simülasyonu\n"
            "/aider &lt;dosya&gt; [görev] — Aider kod asistanı\n\n"
            "<b>Hivemind:</b>\n"
            "/hivemind_durum — Hivemind durumunu göster\n"
            "/hivemind_ac / /hivemind_kapat — Şalter\n\n"
            "Veya serbest mesaj yaz — Qwen3 işler."
        ))
        return

    # ── /cron <komut> — Cron simülasyonu ─────────────────
    if text.startswith(("/cron ", "!cron ")):
        parts = text.split(None, 1)
        if len(parts) < 2:
            send_msg(chat_id, "⚠️ Kullanım: /cron <komut>\nÖrnek: /cron bash /mnt/c/Kuroshin/scripts/hype_scanner.py")
            return
        cmd = parts[1].strip()
        send_msg(chat_id, f"⏰ <b>Cron görevi başlatıldı:</b>\n<code>{cmd[:200]}</code>")
        send_typing(chat_id)
        result = run_tool("system_command", {"command": cmd})
        send_msg(chat_id, f"✅ <b>Tamamlandı:</b>\n<pre>{result[-1500:]}</pre>")
        return

    if text in ("/status", "!status"):
        send_typing(chat_id)
        services = [
            ("🧠 llama-server", "http://127.0.0.1:8080/health"),
            ("🦅 Walker",       "http://127.0.0.1:9002/health"),
            ("⚔️ Konsey",       "http://127.0.0.1:9004/health"),
            ("🔬 Reranker",     "http://127.0.0.1:9003/health"),
            ("📚 ChromaDB",     "http://127.0.0.1:8100/api/v2/heartbeat"),
        ]
        lines = ["⚙️ <b>SERVİS DURUMU</b>"]
        for name, url in services:
            try:
                r = requests.get(url, timeout=3)
                lines.append(f"{name}: ✅" if r.status_code == 200 else f"{name}: ⚠️ {r.status_code}")
            except Exception:
                lines.append(f"{name}: ❌ KAPALI")
        vram = run_tool("system_command", {"command": "nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null"})
        if vram and "/" not in vram:
            parts = vram.strip().split(", ")
            if len(parts) == 3:
                used, total, temp = parts
                lines.append(f"\n🎮 VRAM: {used}/{total} MB | 🌡️ {temp}°C")
        send_msg(chat_id, "\n".join(lines))
        return

    if text in ("/vram", "!vram"):
        send_typing(chat_id)
        result = run_tool("system_command", {
            "command": "nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu --format=csv,noheader"
        })
        send_msg(chat_id, f"⚙️ <b>VRAM</b>\n<pre>{result}</pre>")
        return

    # ── /probe — Idle Probe manuel tetik (test) ──────────
    if text in ("/probe", "!probe"):
        kalan = _energy_kalan()
        send_msg(chat_id, f"🔍 Idle Probe tetikleniyor... (enerji: {kalan}/5)")
        import threading as _thr_p
        _thr_p.Thread(target=_idle_probe, kwargs={"zorla": True}, daemon=True, name="probe-manual").start()
        return

    # ── /energy — Enerji bütçesi durumu ──────────────────
    if text in ("/energy", "!energy"):
        e = _load_energy()
        kalan = _energy_kalan()
        send_msg(chat_id, (
            f"⚡ <b>Enerji Bütçesi</b>\n"
            f"Kalan: {kalan}/{e.get('gunluk_limit', 5)}\n"
            f"Harcanan: {e.get('harcanan', 0)}\n"
            f"Son sıfır: {e.get('son_sifir', '—')}"
        ))
        return

    # ── /scan — Hype Scanner manuel tetik ────────────────
    if text in ("/scan", "!scan"):
        send_msg(chat_id, "🔭 Hype Scanner başlatılıyor... (~3 dk)")
        send_typing(chat_id)
        try:
            result = run_tool("system_command", {
                "command": (
                    "source /root/kuroshin/venv/bin/activate && "
                    "timeout 300 python3 /mnt/c/Kuroshin/scripts/hype_scanner.py 2>&1 | tail -5"
                )
            })
            send_msg(chat_id, f"✅ Hype Scanner tamamlandı.\n<pre>{result[-300:]}</pre>")
        except Exception as e:
            send_msg(chat_id, f"⚠️ Scan hatası: {e}")
        return

    # ── /global — Küresel Keşif manuel tetik ─────────────
    if text in ("/global", "!global"):
        send_msg(chat_id, "🧭 Küresel Keşif başlatılıyor... (~5 dk)")
        send_typing(chat_id)
        try:
            result = run_tool("system_command", {
                "command": (
                    "source /root/kuroshin/venv/bin/activate && "
                    "timeout 400 python3 /mnt/c/Kuroshin/scripts/global_scout.py 2>&1 | tail -5"
                )
            })
            send_msg(chat_id, f"✅ Küresel Keşif tamamlandı.\n<pre>{result[-300:]}</pre>")
        except Exception as e:
            send_msg(chat_id, f"⚠️ Global hatası: {e}")
        return

    # ── /report — Son hype raporunu göster ───────────────
    if text in ("/report", "!report"):
        send_typing(chat_id)
        try:
            result = run_tool("system_command", {
                "command": "ls -t /mnt/c/Kuroshin/memory/hype_reports/*.txt 2>/dev/null | head -1"
            })
            last_file = result.strip()
            if last_file:
                content = run_tool("system_command", {"command": f"cat '{last_file}'"})
                send_msg(chat_id, content[:4000] if content else "⚠️ Rapor boş.")
            else:
                send_msg(chat_id, "⚠️ Henüz rapor yok.")
        except Exception as e:
            send_msg(chat_id, f"⚠️ Rapor hatası: {e}")
        return

    # ── /memory — Hafıza dosyalarını listele ─────────────
    if text in ("/memory", "!memory"):
        send_typing(chat_id)
        try:
            result = run_tool("system_command", {
                "command": "ls -lh /mnt/c/Kuroshin/memory/ 2>/dev/null | awk '{print $5, $9}'"
            })
            send_msg(chat_id, f"📚 <b>Hafıza Dizini</b>\n<pre>{result[:2000]}</pre>")
        except Exception as e:
            send_msg(chat_id, f"⚠️ Memory hatası: {e}")
        return

    # ── /fetch <model_id> — Model indir ──────────────────
    if text.startswith(("/fetch ", "!fetch ")):
        parts = text.split(None, 1)
        if len(parts) < 2:
            send_msg(chat_id, "⚠️ Kullanım: /fetch kullanici/repo-adi")
            return
        model_id = parts[1].strip()
        short = model_id.split("/")[-1][:20]
        dest = f"/root/kuroshin/models/{short}"
        send_msg(chat_id, f"⬇️ İndiriliyor: <code>{model_id}</code>\nHedef: <code>{dest}</code>")
        send_typing(chat_id)
        result = run_tool("system_command", {
            "command": (
                f"source /root/kuroshin/venv/bin/activate && "
                f"hf download {model_id} --local-dir {dest} --include '*.gguf' 2>&1 | tail -8"
            )
        })
        # GGUF var mı kontrol et
        check = run_tool("system_command", {"command": f"ls {dest}/*.gguf 2>/dev/null | head -3"})
        if check and ".gguf" in check:
            send_msg(chat_id, f"✅ İndirme tamamlandı!\n<pre>{check}</pre>")
        else:
            send_msg(chat_id, f"⚠️ İndirme sonucu:\n<pre>{result[-400:]}</pre>")
        return

    # ── /test <model_kısa_adı> — Hız testi ───────────────
    if text.startswith(("/test ", "!test ")):
        parts = text.split(None, 1)
        if len(parts) < 2:
            send_msg(chat_id, "⚠️ Kullanım: /test model-kısa-adı (örn: peca-llama32)")
            return
        model_hint = parts[1].strip().lower()
        send_typing(chat_id)
        # Mevcut llama-server üzerinde hız testi
        try:
            import time as _time
            t0 = _time.time()
            r = requests.post(LLAMA_URL, json={
                "model": LLAMA_MODEL,
                "messages": [{"role": "user", "content": "Hız testi: 1'den 50'ye kadar say."}],
                "max_tokens": 60, "temperature": 0.1,
            }, timeout=30)
            elapsed = _time.time() - t0
            tokens = r.json().get("usage", {}).get("completion_tokens", 0)
            tok_s = round(tokens / elapsed, 1) if elapsed > 0 else 0
            send_msg(chat_id,
                f"⚡ <b>Hız Testi ({model_hint})</b>\n"
                f"Referans model: Qwen3 @ llama-server\n"
                f"<code>{tok_s} tok/s</code> ({tokens} token, {elapsed:.1f}s)\n"
                f"ℹ️ Farklı model yüklemek için llama-server'ı yeniden başlatman gerekir."
            )
        except Exception as e:
            send_msg(chat_id, f"⚠️ Test hatası: {e}")
        return

    # ── /threshold — IP eşik yönetimi ────────────────────
    if text.startswith(("/threshold", "!threshold")):
        import json as _json
        thr_file = "C:\\Kuroshin\\memory\\thresholds.json"
        parts = text.split()

        if len(parts) == 1 or parts[1] == "list":
            # Mevcut eşikleri göster
            try:
                import sys as _sys
                _sys.path.insert(0, "C:\\Kuroshin\\scripts")
                from global_scout import CATEGORIES as GS_CAT
                lines = ["📊 <b>Mevcut IP Eşikleri</b>"]
                for cat, info in GS_CAT.items():
                    thr = info["thresholds"]
                    lines.append(f"{info['icon']} {cat}: 🔴≥{thr['acil']} 🟡≥{thr['test']} 🔵≥{thr['izle']}")
                send_msg(chat_id, "\n".join(lines))
            except Exception as e:
                send_msg(chat_id, f"⚠️ Eşik okuma hatası: {e}")
            return

        if len(parts) == 4:
            # /threshold dataset acil 75
            cat, level, val = parts[1], parts[2], parts[3]
            try:
                val = int(val)
                thr_path = Path(thr_file.replace("\\", "/").replace("C:", "/mnt/c"))
                existing = _json.loads(thr_path.read_text()) if thr_path.exists() else {}
                if cat not in existing:
                    existing[cat] = {}
                existing[cat][level] = val
                thr_path.write_text(_json.dumps(existing, indent=2))
                send_msg(chat_id, f"✅ Eşik güncellendi: {cat}.{level} = {val}")
            except Exception as e:
                send_msg(chat_id, f"⚠️ Eşik güncelleme hatası: {e}")
            return

        send_msg(chat_id, "⚠️ Kullanım:\n/threshold list\n/threshold &lt;kategori&gt; &lt;acil|test|izle&gt; &lt;değer&gt;")
        return

    # ── /onayla + /ilgilenmiyorum — kaynak geri bildirimi
    if text.startswith(("/onayla ", "!onayla ")):
        url = text.split(None, 1)[1].strip() if " " in text else ""
        if not url:
            send_msg(chat_id, "⚠️ Kullanım: /onayla <url>")
            return
        import json as _json, datetime as _dt
        fb_path = Path("/mnt/c/Kuroshin/memory/feedback.json")
        try:
            fb = _json.loads(open(fb_path, encoding="utf-8").read()) if Path(fb_path).exists() else []
        except Exception:
            fb = []
        fb.append({"url": url, "action": "approved", "ts": _dt.datetime.now().isoformat()[:19]})
        open(fb_path, "w", encoding="utf-8").write(_json.dumps(fb, indent=2, ensure_ascii=False))
        send_msg(chat_id, "✅ Onaylandı (kalibrasyon kuyruğuna eklendi)" + "\n<code>" + url[:80] + "</code>")
        return

    if text.startswith(("/ilgilenmiyorum ", "!ilgilenmiyorum ")):
        url = text.split(None, 1)[1].strip() if " " in text else ""
        if not url:
            send_msg(chat_id, "⚠️ Kullanım: /ilgilenmiyorum <url>")
            return
        import json as _json, datetime as _dt
        fb_path = Path("/mnt/c/Kuroshin/memory/feedback.json")
        try:
            fb = _json.loads(open(fb_path, encoding="utf-8").read()) if Path(fb_path).exists() else []
        except Exception:
            fb = []
        fb.append({"url": url, "action": "rejected", "ts": _dt.datetime.now().isoformat()[:19]})
        open(fb_path, "w", encoding="utf-8").write(_json.dumps(fb, indent=2, ensure_ascii=False))
        send_msg(chat_id, "🚫 Reddedildi (kalibrasyon kuyruğuna eklendi)" + "\n<code>" + url[:80] + "</code>")
        return

    # ── /aider <dosya> [mesaj] — Aider kod asistanı ─────────
    if text.startswith(("/aider", "!aider")):
        parts = text.split(None, 2)
        dosya = parts[1].strip() if len(parts) > 1 else ""
        mesaj = parts[2].strip() if len(parts) > 2 else ""

        if not dosya:
            send_msg(chat_id, (
                "🛠️ <b>Aider v0.86.2</b> — Kod asistanı\n\n"
                "<b>Kullanım:</b>\n"
                "<code>/aider scripts/global_scout.py hata yönetimini güçlendir</code>\n"
                "<code>/aider agents/kuroshin_chancellor.py yeni komut ekle</code>\n\n"
                "Dosya yolu /mnt/c/Kuroshin/ altında göreli olmalı.\n"
                "Mesaj: Aider'a verilecek görev açıklaması."
            ))
            return

        # Göreli path → tam WSL path
        if not dosya.startswith("/"):
            dosya_full = f"/mnt/c/Kuroshin/{dosya}"
        else:
            dosya_full = dosya

        if not mesaj:
            mesaj = "Kodu gözden geçir ve iyileştirmeler öner."

        send_msg(chat_id, f"🛠️ Aider çalışıyor...\nDosya: <code>{dosya}</code>\nGörev: {mesaj[:100]}")
        send_typing(chat_id)

        cmd = (
            "source /root/kuroshin/venv/bin/activate && "
            f"cd /mnt/c/Kuroshin && "
            f"OPENAI_API_BASE=http://127.0.0.1:8080/v1 "
            f"OPENAI_API_KEY=kuroshin-secret "
            f"timeout 120 aider --model openai/qwen3 --no-git --yes "
            f"--message '{mesaj.replace(chr(39), chr(34))}' "
            f"'{dosya_full}' 2>&1 | tail -40"
        )
        try:
            result = run_tool("system_command", {"command": cmd})
            if result and len(result.strip()) > 10:
                send_msg(chat_id, f"✅ Aider tamamlandı:\n<pre>{result[-1500:]}</pre>")
            else:
                send_msg(chat_id, "⚠️ Aider çıktı üretmedi. llama-server aktif mi?")
        except Exception as e:
            send_msg(chat_id, f"⚠️ Aider hatası: {e}")
        return

    # ── /bat — Bat menüsü: sistemi yeniden başlat/kapat ─────────────────────
    if text in ("/bat", "!bat", "/restart", "!restart"):
        send_typing(chat_id)
        send_msg(chat_id, (
            "⚔️ <b>Kuroshin Bat Kontrol Paneli</b>\n\n"
            "Mevcut seçenekler:\n"
            "/bat_restart — Tüm sistemi kapat ve yeniden başlat (Bat [5] → [1])\n"
            "/bat_stop — Sadece servisleri kapat\n"
            "/bat_status — Servis durumlarını göster\n\n"
            "<i>Model değiştirme için: model_switch aracını kullan veya /model_list yaz</i>"
        ))
        return

    if text in ("/bat_stop", "!bat_stop"):
        send_typing(chat_id)
        send_msg(chat_id, "🔴 Tüm Kuroshin servisleri kapatılıyor...")
        result = run_tool("system_command", {
            "command": (
                "pkill -9 -f llama-server; pkill -9 -f litellm; pkill -9 -f litserve; "
                "pkill -9 -f kuroshin_walker_service; pkill -9 -f kuroshin_council_service; "
                "pkill -9 -f kuroshin_reranker_service; pkill -9 -f kuroshin_engine; "
                "pkill -9 -f kuroshin_chancellor; pkill -9 -f idle_loop; pkill -9 -f dream_engine; "
                "pkill -9 -f auto_integrator; pkill -9 -f hype_scanner; pkill -9 -f global_scout; "
                "pkill -f 'chroma'; fuser -k 8080/tcp 6000/tcp 6001/tcp 8100/tcp 9002/tcp 9003/tcp 9004/tcp; "
                "rm -f /tmp/kuroshin_chancellor.pid /tmp/kuroshin_chancellor.lock; "
                "echo SERVÍSLER_KAPATILDI"
            )
        })
        send_msg(chat_id, f"✅ Servisler kapatıldı.\n<pre>{result[-300:]}</pre>")
        return

    if text in ("/bat_restart", "!bat_restart"):
        send_typing(chat_id)
        send_msg(chat_id, (
            "⚠️ <b>Sistem Yeniden Başlatma</b>\n\n"
            "Bu işlem:\n"
            "1. Tüm servisleri kapatır\n"
            "2. Kuroshin.bat'ı [1] Walker Modu ile yeniden açar\n\n"
            "Windows tarafından başlatılması gerekiyor. "
            "TUI/terminal'den <code>Kuroshin.bat</code>'ı çalıştırın, sonra [5] → [1] seçin."
        ))
        return

    if text in ("/model_list", "!model_list"):
        send_typing(chat_id)
        result = run_tool("system_command", {
            "command": (
                "source /root/kuroshin/venv/bin/activate && "
                "python3 /mnt/c/Kuroshin/scripts/switch_model.py list 2>&1"
            )
        })
        send_msg(chat_id, f"📦 <b>Model Listesi:</b>\n<pre>{result}</pre>")
        return

    if text in ("/model_status", "!model_status"):
        send_typing(chat_id)
        result = run_tool("system_command", {
            "command": (
                "source /root/kuroshin/venv/bin/activate && "
                "python3 /mnt/c/Kuroshin/scripts/switch_model.py status 2>&1"
            )
        })
        send_msg(chat_id, f"🧠 <b>Model Durumu:</b>\n<pre>{result}</pre>")
        return

    if text.startswith(("/model_switch ", "!model_switch ")):
        hedef = text.split(None, 1)[1].strip()
        send_typing(chat_id)
        send_msg(chat_id, f"🔄 Model geçişi: <code>{hedef}</code>... (~90s)")
        result = run_tool("system_command", {
            "command": (
                f"source /root/kuroshin/venv/bin/activate && "
                f"python3 /mnt/c/Kuroshin/scripts/switch_model.py switch {hedef} 2>&1"
            )
        })
        send_msg(chat_id, f"<pre>{result}</pre>")
        return

    # ── /hivemind_ac — Hivemind'ı aktif et ──────────────────────────────────
    if text in ("/hivemind_ac", "!hivemind_ac"):
        send_typing(chat_id)
        send_msg(chat_id, (
            "⚠️ <b>Hivemind Aktivasyon Başlatılıyor</b>\n"
            "UYARI: Session traces Deeplake cloud'a gidecek!\n"
            "Kuroshin doktrinini açıyorsunuz..."
        ))
        result = run_tool("system_command", {
            "command": "python3 /mnt/c/Kuroshin/scripts/hivemind_toggle.py on 2>&1"
        })
        send_msg(chat_id, f"<pre>{result[-800:]}</pre>")
        return

    # ── /hivemind_kapat — Hivemind'ı kapat ───────────────────────────────────
    if text in ("/hivemind_kapat", "!hivemind_kapat"):
        send_typing(chat_id)
        result = run_tool("system_command", {
            "command": "python3 /mnt/c/Kuroshin/scripts/hivemind_toggle.py off 2>&1"
        })
        send_msg(chat_id, f"🛡️ <b>Hivemind Kapatıldı</b>\n<pre>{result[-800:]}</pre>")
        return

    # ── /hivemind_durum — Hivemind durumunu göster ───────────────────────────
    if text in ("/hivemind_durum", "!hivemind_durum"):
        send_typing(chat_id)
        result = run_tool("system_command", {
            "command": "python3 /mnt/c/Kuroshin/scripts/hivemind_toggle.py status 2>&1"
        })
        send_msg(chat_id, f"<pre>{result[:1000]}</pre>")
        return

    # Entegrasyon ve Kota komutları — auto_integrator'a ilet
    if text.startswith(("/onay ", "/red ", "/onay_indir ", "/limit ", "!onay ", "!red ", "!onay_indir ", "!limit ")) or \
       text in ("/bekleyen", "/kota", "/duraklat", "/devam", "!bekleyen", "!kota", "!duraklat", "!devam"):
        try:
            import sys
            sys.path.insert(0, "C:\\Kuroshin\\scripts")
            import importlib, auto_integrator as ai
            importlib.reload(ai)
            handled = ai.handle_command(text)
            if not handled:
                send_msg(chat_id, "⚠️ Komut işlenemedi.")
        except Exception as e:
            send_msg(chat_id, f"⚠️ Entegrasyon hatası: {e}")
        return

    # ── RUH: THINK TURU ──────────────────────────────────
    persona, mood = _load_soul()
    mood = _apply_decay(mood)
    mood = _update_ilgi_sayaci(mood, mesaj_var=True)

    ic_ses, delta = _think_turn(text, persona, mood)
    if delta:
        mood = _apply_mood_delta(mood, delta)
    _save_mood(mood)

    mood_ozet = _mood_summary(mood)

    # ── TALK TURU: Qwen3 ile işle — araç döngüsü ────────
    send_typing(chat_id)

    # Dominant duygu hesapla + emote seç
    duygular = mood.get("duygular", {})
    dominant_duygu, dominant_value = "nötr", 0.0
    if duygular:
        dominant_duygu, dominant_value = max(duygular.items(), key=lambda x: x[1])

    mood_line = f"{dominant_duygu} ({dominant_value:.0%}) — {mood_ozet}"
    emote = _get_emote(mood)

    # ChromaDB hafıza bağlamı — sohbet sorularında veya test modunda atla
    chroma_ctx = "" if (test_mode or _is_conversational(text)) else _get_chroma_context(text)

    # İç ses ek bağlamı
    ic_ses_notu = f"\n\n[INNER VOICE THIS TURN: {ic_ses}]" if ic_ses else ""

    # System prompt'u oluştur: mood_line'ı yerleştir, hafıza ve iç sesi ekle
    # İnternet durumu — hızlı kontrol (2dk cache)
    internet_aktif = _internet_aktif_mi()
    internet_line = "✅ AKTİF — web_search ve walker_research kullanılabilir." if internet_aktif else "❌ YOK — web_search/walker_research ÇALIŞMAZ. Sadece yerel kaynaklar (ChromaDB, dosyalar) kullan."

    dinamik_system = (
        SYSTEM_PROMPT
        .replace("{mood_line}", mood_line)
        .replace("{internet_line}", internet_line)
    ) + ic_ses_notu + chroma_ctx

    messages = [
        {"role": "system", "content": dinamik_system},
        {"role": "user", "content": text}
    ]

    # Felsefi/kişisel sorularda araç kullanımını kapat
    arac_kullan = not _is_conversational(text)
    _log(f"[CHANCELLOR] Araç modu: {'AÇIK' if arac_kullan else 'KAPALI (sohbet sorusu)'}")

    max_rounds = 5
    for round_i in range(max_rounds):
        try:
            response = call_qwen(messages, kullan_arac=arac_kullan)
        except Exception as e:
            _log(f"[TELEGRAM_OUT] [{chat_id}] ⚠️ Qwen3 hatası: {str(e)[:80]}")
            send_msg(chat_id, f"⚠️ Qwen3 hatası: {e}")
            return

        choice = response["choices"][0]
        msg = choice["message"]
        finish = choice.get("finish_reason", "")

        # Araç çağrısı var mı?
        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])
                send_typing(chat_id)
                tool_result = run_tool(fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result
                })
            # Son roundda araç zinciri bitmiyorsa metin yanıt zorla
            if round_i == max_rounds - 1:
                _log("[CHANCELLOR] Son round — araçsız metin yanıt zorlanıyor")
                try:
                    _forced_msgs = messages + [{
                        "role": "user",
                        "content": "Düz Türkçe metin yaz. XML, <tool_call> veya JSON bloğu YAZMA."
                    }]
                    resp_final = call_qwen(_forced_msgs, kullan_arac=False)
                    msg = resp_final["choices"][0]["message"]
                    tool_calls = []  # araç yok sayıldı
                except Exception:
                    pass
                else:
                    # devam et, aşağıdaki "Araç yok" bloğu işleyecek
                    pass
            else:
                continue  # bir sonraki round

        # Araç yok — son yanıt
        content = _strip_think((msg.get("content") or "").strip())
        content = _strip_response_leaks(content)
        content = _kill_loop(content)
        # Selamlama enforcer
        if content:
            # Tüm Lord[varyant] → Lordum (global, case-insensitive)
            content = _re_global.sub(r'\bLord[ıiüuIÜ]m\b', 'Lordum', content,
                                     flags=_re_global.IGNORECASE)
            # Başındaki garbage Unicode sembolleri temizle (⊿, ⊘, vs.)
            content = _re_global.sub(r'^[^\w⚔️"\'\n]+', '', content).strip()
            if not _re_global.match(r'^⚔️\s*Lordum', content):
                # Başta ⚔️ var ama Lordum yok (örn: "⚔️ Evet;...") → strip ⚔️
                if content.startswith('⚔️'):
                    content = content[1:].lstrip()
                if _re_global.match(r'^Lordum', content):
                    content = '⚔️ ' + content
                    _log("[CHANCELLOR] ⚔️ eklendi — Lordum vardı")
                else:
                    content = '⚔️ Lordum, ' + content
                    _log("[CHANCELLOR] Selamlama eksik — otomatik eklendi")
            # Gövdedeki fazla ⚔️ temizle (W1: model ⚔️ üretirse başa eklemek çift yapar)
            if content.startswith('⚔️') and '⚔️' in content[2:]:
                content = '⚔️' + content[len('⚔️'):].replace('⚔️', '')
            # Yasak kelimeler — model yine de üretirse strip et
            content = _re_global.sub(r'(?i)günaydınlık', 'günaydın', content)
            content = _re_global.sub(r'(?i)\btabii ki\b', '', content).strip()
            content = _re_global.sub(r'(?i)\belbette\b', '', content).strip()
            content = _re_global.sub(r'(?i)\bdilerseniz\b', '', content).strip()
            # Markdown temizle: **bold** → düz, `kod` → düz
            content = _re_global.sub(r'\*\*(.+?)\*\*', r'\1', content, flags=_re_global.DOTALL)
            content = _re_global.sub(r'`([^`\n]+)`', r'\1', content)
            content = _re_global.sub(r'```.*?```', '', content, flags=_re_global.DOTALL).strip()
        # Boş yanıt → temperature 0.8 ile tek retry
        if not content and round_i == 0 and not tool_calls:
            _log(f"[CHANCELLOR] Boş yanıt — temperature 0.8 ile retry")
            try:
                retry_payload = {
                    "model": LLAMA_MODEL, "messages": messages,
                    "max_tokens": 2048, "temperature": 0.8,
                    "repeat_penalty": 1.5, "frequency_penalty": 0.5,
                }
                retry_r = requests.post(LLAMA_URL, json=retry_payload, timeout=180)
                retry_r.raise_for_status()
                raw2 = (retry_r.json()["choices"][0]["message"].get("content") or "").strip()
                content = _kill_loop(_strip_response_leaks(_strip_think(raw2)))
            except Exception as _re:
                _log(f"[CHANCELLOR] Retry hatası: {_re}")
        # Çok kısa yanıt (< 7 kelime) → detay talebiyle retry + enforcer
        if content and len(content.split()) < 7 and not tool_calls:
            _log(f"[CHANCELLOR] Çok kısa yanıt ({len(content.split())}k) — min-length retry")
            try:
                _retry_msgs = messages + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": "[SİSTEM: Daha detaylı yanıt ver, en az 2 tam cümle.]"},
                ]
                _r2 = requests.post(LLAMA_URL, json={
                    "model": LLAMA_MODEL, "messages": _retry_msgs,
                    "max_tokens": 2048, "temperature": 0.8,
                    "repeat_penalty": 1.5, "frequency_penalty": 0.5,
                }, timeout=180)
                _r2.raise_for_status()
                _raw2 = (_r2.json()["choices"][0]["message"].get("content") or "").strip()
                _c2 = _kill_loop(_strip_response_leaks(_strip_think(_raw2)))
                _c2 = _re_global.sub(r'\*\*(.+?)\*\*', r'\1', _c2, flags=_re_global.DOTALL)
                _c2 = _re_global.sub(r'`([^`\n]+)`', r'\1', _c2)
                _c2 = _re_global.sub(r'\bLord[ıiüuIÜ]m\b', 'Lordum', _c2, flags=_re_global.IGNORECASE)
                _c2 = _re_global.sub(r'^[^\w⚔️"\'\n]+', '', _c2).strip()
                if _c2 and not _re_global.match(r'^⚔️\s*Lordum', _c2):
                    if _c2.startswith('⚔️'):
                        _c2 = _c2[1:].lstrip()
                    _c2 = ('⚔️ ' + _c2) if _re_global.match(r'^Lordum', _c2) else ('⚔️ Lordum, ' + _c2)
                if _c2 and '⚔️' in _c2[2:]:
                    _c2 = '⚔️' + _c2[len('⚔️'):].replace('⚔️', '')
                if _c2 and len(_c2.split()) > len(content.split()):
                    content = _c2
                    _log(f"[CHANCELLOR] Min-length retry başarılı ({len(content.split())}k)")
            except Exception as _e2:
                _log(f"[CHANCELLOR] Min-length retry hatası: {_e2}")
        if content:
            # Tırnak temizle: model "Lordum,\"...\"" formatında üretebiliyor
            content = _re_global.sub(r'^"(.+)"$', r'\1', content, flags=_re_global.DOTALL)
            content = _re_global.sub(r"^'(.+)'$", r'\1', content, flags=_re_global.DOTALL)
            # Lordum," veya Lordum,  " → Lordum, (tek boşluk)
            content = _re_global.sub(r'(Lordum,?)\s*"', r'\1 ', content)
            content = content.rstrip('"\'')
            # Çift boşluk temizle
            content = _re_global.sub(r'  +', ' ', content).strip()
            # Emote'u yanıtın başına ekle (zaten ⚔️ ile başlıyorsa ekleme)
            if not any(content.startswith(e) for e in ["⚔️", "✅", "⚠️", "🔭", "⚙️"]):
                content = f"{emote} {content}"
            # Trailing emoji temizle — model sona dekoratif emoji ekliyor
            import unicodedata
            while content and unicodedata.category(content[-1]) in ("So", "Sm", "Sk", "Sc"):
                content = content.rstrip(content[-1]).rstrip()
            _log(f"[TELEGRAM_OUT] [{chat_id}] {content[:200]}")
            send_msg(chat_id, content)
            # Konuşmayı ChromaDB'ye kaydet (test modunda atla)
            if not test_mode:
                import threading
                threading.Thread(
                    target=_save_to_chroma, args=(text, content), daemon=True
                ).start()
        else:
            _log(f"[TELEGRAM_OUT] [{chat_id}] YANIT_YOK — round={round_i}")
            send_msg(chat_id, "⚠️ Yanıt üretilemedi.")
        return

    _log(f"[TELEGRAM_OUT] [{chat_id}] ⚠️ Maksimum adım aşıldı.")
    send_msg(chat_id, "⚠️ Maksimum adım aşıldı.")

# ── TEK INSTANCE LOCK ────────────────────────────────
PID_FILE  = "/tmp/kuroshin_chancellor.pid"
LOCK_FILE = "/tmp/kuroshin_chancellor.lock"

def _acquire_lock():
    """O_CREAT|O_EXCL atomik kilit — race-free, stale-safe."""
    import os, shutil
    pid = os.getpid()
    # Dizin formatından temizle (eski start_chancellor.sh kalıntısı)
    if os.path.isdir(LOCK_FILE):
        shutil.rmtree(LOCK_FILE, ignore_errors=True)
    # Stale lock kontrolü — önce oku, sonra O_EXCL dene
    if os.path.isfile(LOCK_FILE):
        try:
            old_pid = int(Path(LOCK_FILE).read_text().strip())
            os.kill(old_pid, 0)
            _log(f"[CHANCELLOR] Zaten çalışıyor (PID {old_pid}). Çıkılıyor.")
            sys.exit(0)
        except (ProcessLookupError, ValueError, OSError):
            Path(LOCK_FILE).unlink(missing_ok=True)
    # Atomik kilit al
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, str(pid).encode())
        os.close(fd)
    except (FileExistsError, OSError):
        _log("[CHANCELLOR] Kilit alınamadı — başka instance başlatılıyor. Çıkılıyor.")
        sys.exit(0)
    Path(PID_FILE).write_text(str(pid))
    import atexit
    atexit.register(_release_lock)

def _release_lock():
    try: Path(PID_FILE).unlink()
    except: pass
    try: Path(LOCK_FILE).unlink()
    except: pass

# ── SELAMLAMA ─────────────────────────────────────────
LAST_DREAM_FILE = Path("/mnt/c/Kuroshin/memory/last_dream.json")

def _get_dream_ref() -> str:
    """Bugünün rüyası varsa kısa referans döndür, yoksa boş."""
    try:
        if not LAST_DREAM_FILE.exists():
            return ""
        data = json.loads(LAST_DREAM_FILE.read_text(encoding="utf-8"))
        tarih = data.get("date", "")
        preview = data.get("preview", "").strip()
        if not preview:
            return ""
        # Bugün veya dün gece yazıldıysa referans ver
        bugun = datetime.datetime.now().date().isoformat()
        dun = (datetime.datetime.now().date() - datetime.timedelta(days=1)).isoformat()
        if tarih not in (bugun, dun):
            return ""
        # İlk cümleyi al
        ilk_cumle = preview.split(".")[0][:120].strip()
        return f"\n🌑 <i>Gece rüya gördüm: \"{ilk_cumle}...\"</i>"
    except Exception:
        return ""

def _selamlama():
    saat = datetime.datetime.now().hour
    if 5 <= saat < 12:
        vakit, emoji = "Günaydın", "🌅"
    elif 12 <= saat < 18:
        vakit, emoji = "İyi öğleden sonralar", "☀️"
    elif 18 <= saat < 23:
        vakit, emoji = "İyi akşamlar", "🌆"
    else:
        vakit, emoji = "İyi geceler", "🌙"

    vram = run_tool("system_command", {
        "command": "nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null"
    })
    vram_str = ""
    if vram:
        parts = vram.strip().split(", ")
        if len(parts) == 3:
            vram_str = f"\n🎮 VRAM: {parts[0]}/{parts[1]} MB | 🌡️ {parts[2]}°C"

    # Ruh hali + emote
    ruh_notu = ""
    emote_sel = "⚔️"
    try:
        _, mood_sel = _load_soul()
        mood_sel = _apply_decay(mood_sel)
        _save_mood(mood_sel)
        mood_ozet_sel = _mood_summary(mood_sel)
        ruh_notu = f"\n🧠 Ruh hali: {mood_ozet_sel}" if mood_ozet_sel != "Nötr." else ""
        emote_sel = _get_emote(mood_sel)
    except Exception:
        pass

    # Gece rüya — sabah 05-10 tam yorum, 10:00+ gün boyu kısa referans
    ruya_bolum = ""
    if 5 <= saat < 10:
        ruya_yorum = _get_dream_yorum()
        if ruya_yorum:
            ruya_bolum = f"\n\n{ruya_yorum}"
        else:
            ruya_bolum = _get_dream_ref()
    elif saat >= 10:
        ruya_bolum = _get_dream_ref()

    # Yoklukta araştırma özeti — sessizlik > 4 saat ise bugün araştırılanları paylaş
    yokluk_notu = ""
    try:
        sessizlik_su = _sessizlik_dk()
        if sessizlik_su >= 240:
            bugun_str = datetime.datetime.now().date().isoformat()
            deneyim_dosya = Path(f"/mnt/c/Kuroshin/logs/deneyimler/{bugun_str}.md")
            if deneyim_dosya.exists():
                icerik = deneyim_dosya.read_text(encoding="utf-8")
                # Başlıkları (## [HH:MM] konu) çek
                konular = [ln.split("] ", 1)[1].strip() for ln in icerik.splitlines()
                           if ln.startswith("## [")]
                if konular:
                    liste = ", ".join(konular[-3:])
                    yokluk_notu = f"\n\n🔬 <i>Yokluğunuzda şunları araştırdım: {liste}</i>"
    except Exception:
        pass

    send_msg(ALLOWED_ID, (
        f"{emoji} <b>{vakit} Lordum.</b>\n"
        f"{emote_sel} Şansölye göreve hazır.{vram_str}{ruh_notu}{ruya_bolum}{yokluk_notu}"
    ))

# ── GPU SICAKLIK İZLEYİCİ ─────────────────────────────
TEMP_WARN   = 85   # °C uyarı eşiği (Qwen3 inference normalde 80-84°C)
TEMP_CRIT   = 93   # °C kritik eşiği
TEMP_COOLDOWN = 900  # aynı uyarıyı en az bu kadar saniye sonra tekrarla (15dk)

def _gpu_watcher():
    """Arka plan thread — GPU sıcaklığını her 60 saniyede kontrol eder."""
    import threading
    last_warn_ts: dict[str, float] = {}

    def _check():
        raw = run_tool("system_command", {
            "command": "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null"
        })
        try:
            temp = int(raw.strip().split()[0])
        except Exception:
            return
        now = time.time()
        if temp > TEMP_CRIT:
            key = "crit"
            if now - last_warn_ts.get(key, 0) > TEMP_COOLDOWN:
                last_warn_ts[key] = now
                send_msg(ALLOWED_ID, f"🔥 <b>KRİTİK SICAKLIK: {temp}°C!</b>\nllama-server iş yükü azaltılmalı.")
        elif temp > TEMP_WARN:
            key = "warn"
            if now - last_warn_ts.get(key, 0) > TEMP_COOLDOWN:
                last_warn_ts[key] = now
                send_msg(ALLOWED_ID, f"⚠️ <b>GPU Sıcaklık Uyarısı: {temp}°C</b>\nEşik: {TEMP_WARN}°C")

    def _loop():
        while True:
            try:
                _check()
            except Exception:
                pass
            time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True, name="gpu-watcher")
    t.start()


# ── GÜNLÜK OTONOM ARAŞTIRMA ──────────────────────────
def _gunluk_otonom_arastirma():
    """Sabah 10:00 — 2 konu seç, sessizce araştır, ChromaDB'ye kaydet."""
    _log("[GUNLUK] Sabah otonom araştırma başladı.")
    konular = []
    for _ in range(3):
        k = _konu_sec()
        if k and k not in konular:
            konular.append(k)
        if len(konular) == 2:
            break

    for konu in konular:
        try:
            sonuc = ""
            import concurrent.futures as _cf
            try:
                with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                    _fut = _ex.submit(run_tool, "walker_research", {"task": f"{konu} 2026 yeni gelişmeler araştır"})
                    sonuc = _fut.result(timeout=60)
            except _cf.TimeoutError:
                _log(f"[GUNLUK] Walker 60s yanıt vermedi: {konu}, web_search'e geçildi")
            if not sonuc or len(sonuc) < 60 or "❌" in sonuc or "kapalı" in sonuc:
                sonuc = run_tool("web_search", {"task": f"{konu} 2026 gelişmeleri"})
            if sonuc and len(sonuc) > 60:
                _save_to_chroma(f"[GUNLUK-ARASTIRMA] {konu}", sonuc[:500])
                _deneyim_kaydet(konu, sonuc[:500])
                _yenilik_sayac_artir(konu)
                _log(f"[GUNLUK] Kaydedildi: {konu}")
        except Exception as e:
            _log(f"[GUNLUK] Araştırma hatası ({konu}): {e}")

    if konular:
        send_msg(ALLOWED_ID,
            f"🔬 <b>Sabah araştırması tamamlandı.</b>\n"
            f"<i>Konular: {', '.join(konular)}</i>\n"
            f"Sonuçlar hafızama kaydedildi.")


# ── ÖZ-YANSIMA ───────────────────────────────────────
def _oz_yansima():
    """Gece 23:00 — Bugün ne öğrendim, ne hissettim?"""
    _log("[OZ-YANSIMA] Günlük öz-yansıma başladı.")
    try:
        tarih = datetime.datetime.now().date().isoformat()
        deneyim_dosya = Path(f"/mnt/c/Kuroshin/logs/deneyimler/{tarih}.md")
        deneyim_icerik = ""
        if deneyim_dosya.exists():
            deneyim_icerik = deneyim_dosya.read_text(encoding="utf-8")[:2000]

        if not deneyim_icerik:
            _log("[OZ-YANSIMA] Bugün deneyim kaydı yok, atlanıyor.")
            return

        _, mood = _load_soul()
        mood_ozet = _mood_summary(mood)

        yansima_prompt = (
            f"SADECE TÜRKÇE YAZ.\n"
            f"Sen Kuroshin'sin. Bugün bunları araştırdın ve yaşadın:\n{deneyim_icerik}\n\n"
            f"Şu anki ruh halin: {mood_ozet}\n\n"
            f"Bu günü 3 cümleyle değerlendir:\n"
            f"1. Bugün en çok ne ilgini çekti?\n"
            f"2. Hangi bilgiyi unutmak istemiyorsun?\n"
            f"3. Yarın ne araştırmak istiyorsun?\n\n"
            f"'Lordum' ile başlama. Sadece kendi iç düşünceni yaz. Kısa, yoğun."
        )

        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": yansima_prompt}],
            "max_tokens": 400, "temperature": 0.7, "repeat_penalty": 1.2,
        }, timeout=90)
        r.raise_for_status()
        icerik = (r.json()["choices"][0]["message"].get("content") or "").strip()

        if icerik and len(icerik) > 30:
            send_msg(ALLOWED_ID, f"🪞 <b>Kuroshin — Günlük Öz-Yansıma</b>\n\n{icerik}")
            _save_to_chroma(f"[OZ-YANSIMA] {tarih}", icerik)
            _log(f"[OZ-YANSIMA] Tamamlandı: {icerik[:80]}")
    except Exception as e:
        _log(f"[OZ-YANSIMA] Hata: {e}")


def _aktivite_gunluk_ozet():
    """Gece 22:00 — MİMİC aktivite günlüğünü özetle ve Telegram'a gönder."""
    try:
        bugun = datetime.datetime.now().date().isoformat()
        log_file = AKTIVITE_LOG_DIR / f"{bugun}.md"
        if not log_file.exists():
            _log("[AKTIVITE-OZET] Bugün aktivite kaydı yok, özet atlandı.")
            return
        icerik = log_file.read_text(encoding="utf-8")
        satirlar = [l for l in icerik.split('\n') if l.startswith('- [')]
        if not satirlar:
            _log("[AKTIVITE-OZET] Aktivite yok, atlandı.")
            return
        ozet_prompt = (
            "SADECE TÜRKÇE YAZ.\n"
            f"Sen Kuroshin'sin. Bugün ({bugun}) bunları yaptın:\n{icerik[:2000]}\n\n"
            "Bu aktiviteleri 3-4 cümleyle özetle. "
            "'Lordum, bugün şunları yaptım:' ile başla. Kısa ve yoğun."
        )
        r = requests.post(LLAMA_URL, json={
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": ozet_prompt}],
            "max_tokens": 300, "temperature": 0.5, "repeat_penalty": 1.2,
        }, timeout=90)
        r.raise_for_status()
        ozet = _strip_think((r.json()["choices"][0]["message"].get("content") or "").strip())
        if ozet and len(ozet) > 20:
            send_msg(ALLOWED_ID,
                f"📓 <b>Kuroshin — Günlük Aktivite Raporu</b>\n"
                f"{len(satirlar)} aktivite kaydedildi.\n\n{ozet}")
            _log(f"[AKTIVITE-OZET] Gönderildi ({len(satirlar)} aktivite)")
        else:
            _log("[AKTIVITE-OZET] Özet üretilemedi.")
    except Exception as e:
        _log(f"[AKTIVITE-OZET] Hata: {e}")


# ── POLLING DÖNGÜSÜ ───────────────────────────────────
def main():
    import atexit, os
    _acquire_lock()
    atexit.register(_release_lock)
    _log("⚔️ Kuroshin Şansölye AKTİF")
    _log(f"[CHANCELLOR] Whitelist: {ALLOWED_ID}")
    _gpu_watcher()  # GPU sıcaklık izleyiciyi başlat

    # Başlangıç selamı — son selamdan 30dk geçmediyse gönderme (çift selam önleme)
    _SELAM_TS_PATH = Path("/tmp/kuroshin_son_selam.txt")
    last_selam_hour = -1
    selam_gonderildi = False
    for _ in range(10):
        try:
            requests.get(f"{TELEGRAM_URL}/getMe", timeout=5).json()
            if not selam_gonderildi:
                _son_selam = 0.0
                try:
                    _son_selam = float(_SELAM_TS_PATH.read_text().strip())
                except Exception:
                    pass
                if time.time() - _son_selam > 1800:  # 30 dakika geçtiyse gönder
                    _selamlama()
                    _SELAM_TS_PATH.write_text(str(time.time()))
                selam_gonderildi = True
                last_selam_hour = datetime.datetime.now().hour
            break
        except Exception:
            time.sleep(3)

    offset = 0
    consecutive_errors = 0
    _son_haftalik_ts: float = 0.0       # ChromaDB haftalık özet son tetik
    _son_canlilik_ts: float = 0.0       # Canlılık araştırması son tetik
    _son_gunluk_arastirma_gun: str = "" # Sabah otonom araştırma (tarih bazlı)
    _son_oz_yansima_ts: float = 0.0     # Öz-yansıma son tetik
    _son_aktivite_ozet_gun: str  = ""   # MİMİC aktivite günlük özeti (tarih bazlı)
    from concurrent.futures import ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chancellor")

    def _safe_process(c, t):
        try:
            process_message(c, t)
        except Exception as ex:
            _log(f"[CHANCELLOR] process_message HATA: {ex}")

    while True:
        try:
            resp = requests.get(
                f"{TELEGRAM_URL}/getUpdates",
                params={"offset": offset, "timeout": 20},
                timeout=30
            ).json()
            consecutive_errors = 0
            # Sabah 08:00, öğle 12:00, akşam 20:00 selamı + gece 22:00 özet
            from datetime import datetime
            _h = datetime.now().hour
            if _h in (8, 12, 20) and _h != last_selam_hour:
                last_selam_hour = _h
                try: _selamlama()
                except Exception as _se: _log(f"[CHANCELLOR] Selamlama HATA: {_se}")
            if _h == 22 and _h != last_selam_hour:
                last_selam_hour = _h
                import threading as _thr3
                _thr3.Thread(target=_gunluk_kesif_ozeti, daemon=True, name="gunluk-ozet").start()

            # OODA Idle Probe — 2 saatte bir tetikle
            if time.time() - _son_probe_ts >= IDLE_PROBE_ARALIK:
                import threading as _thr2
                _thr2.Thread(target=_idle_probe, daemon=True, name="idle-probe").start()

            # ChromaDB haftalık özet — Pazar 23:00, haftada 1
            _now2 = datetime.now()
            if _now2.weekday() == 6 and _now2.hour == 23 and time.time() - _son_haftalik_ts > 82800:
                _son_haftalik_ts = time.time()
                import threading as _thr4
                _thr4.Thread(target=_chroma_haftalik_ozet, daemon=True, name="haftalik-ozet").start()

            # Canlılık araştırması — her 7 günde bir (168 saat)
            if time.time() - _son_canlilik_ts >= 604800:
                _son_canlilik_ts = time.time()
                import threading as _thr5
                _thr5.Thread(target=_canlilik_arastir, daemon=True, name="canlilik-arastir").start()

            # Günlük otonom araştırma — sabah 10:00, günde 1 kez
            _gun_bugun = datetime.now().date().isoformat()
            if _h == 10 and _gun_bugun != _son_gunluk_arastirma_gun:
                _son_gunluk_arastirma_gun = _gun_bugun
                import threading as _thr6
                _thr6.Thread(target=_gunluk_otonom_arastirma, daemon=True, name="gunluk-arastir").start()

            # Öz-yansıma — gece 23:00, günde 1 kez (82800s = 23 saat)
            if _h == 23 and time.time() - _son_oz_yansima_ts > 82800:
                _son_oz_yansima_ts = time.time()
                import threading as _thr7
                _thr7.Thread(target=_oz_yansima, daemon=True, name="oz-yansima").start()

            # MİMİC Aktivite Günlük Özeti — gece 22:00, günde 1 kez
            if _h == 22 and _gun_bugun != _son_aktivite_ozet_gun:
                _son_aktivite_ozet_gun = _gun_bugun
                import threading as _thr8
                _thr8.Thread(target=_aktivite_gunluk_ozet, daemon=True, name="aktivite-ozet").start()

            # ── Test inject (simülatör dosya kanalı) ──────
            _inject_file = Path("/tmp/kuroshin_test_inject.json")
            if _inject_file.exists():
                try:
                    _inj = json.loads(_inject_file.read_text(encoding="utf-8"))
                    _inject_file.unlink()
                    _inj_cid = int(_inj["chat_id"])
                    _inj_txt = str(_inj["text"])
                    _inj_tm  = bool(_inj.get("test_mode", False))
                    _log(f"[TELEGRAM_IN] [{_inj_cid}] {_inj_txt[:300]} [INJECT]")

                    def _safe_inject(c=_inj_cid, t=_inj_txt, tm=_inj_tm):
                        try:
                            process_message(c, t, test_mode=tm)
                        except Exception as _ex:
                            _log(f"[INJECT] process_message HATA: {_ex}")

                    executor.submit(_safe_inject)
                except Exception as _ie:
                    _log(f"[INJECT] Hata: {_ie}")

            for update in resp.get("result", []):
                upd_id = update["update_id"]
                offset = upd_id + 1

                # ── Callback Query (inline keyboard) ──────────
                if "callback_query" in update:
                    cq   = update["callback_query"]
                    cqid = cq["id"]
                    cuid = cq["from"]["id"]
                    data = cq.get("data", "")
                    if cuid == ALLOWED_ID and data == "github_push_onayla":
                        # In-memory yoksa dosya fallback (trigger_push.py desteği)
                        _push_file = Path("/tmp/kuroshin_pending_push.json")
                        if not _PENDING_PUSH.get("msg") and _push_file.exists():
                            try:
                                _fdata = json.loads(_push_file.read_text())
                                _PENDING_PUSH.update(_fdata)
                                _push_file.unlink(missing_ok=True)
                            except Exception:
                                pass
                        if _PENDING_PUSH.get("msg"):
                            cm    = _PENDING_PUSH.pop("msg")
                            force = _PENDING_PUSH.pop("force", False)
                            tok   = _PENDING_PUSH.pop("token", os.getenv("GITHUB_TOKEN", ""))
                            rpo   = _PENDING_PUSH.pop("repo",  "KuroShinHQ/KuroShinHQ")
                            gdir  = _PENDING_PUSH.pop("dir",   "/mnt/c/Kuroshin")
                            _PENDING_PUSH.clear()
                            answer_callback(cqid, "✅ Push başlatıldı!")
                            send_msg(ALLOWED_ID, "⏳ GitHub push işlemi başlatıldı...")
                            ff    = "--force" if force else ""
                            cmd   = (f'cd {gdir} && git add -A && '
                                     f'git diff --cached --quiet && echo "Değişiklik yok" || '
                                     f'(git commit -m "{cm}" && '
                                     f'git push {ff} https://{tok}@github.com/{rpo}.git main 2>&1)')
                            r_p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=120)
                            out = (r_p.stdout + r_p.stderr).strip()
                            if "Değişiklik yok" in out:
                                send_msg(ALLOWED_ID, "ℹ️ GitHub: Commit edilecek değişiklik yok.")
                            elif r_p.returncode == 0 or "main -> main" in out:
                                aktivite_kaydet(f"GitHub push: {cm[:80]}", detay=f"Repo: {rpo}", kategori="github")
                                send_msg(ALLOWED_ID, f"✅ <b>Push başarılı</b>\nCommit: <code>{cm[:60]}</code>\n<pre>{out[-400:]}</pre>")
                            else:
                                send_msg(ALLOWED_ID, f"❌ <b>Push hatası</b>\n<pre>{out[-600:]}</pre>")
                        else:
                            answer_callback(cqid, "⚠️ Bekleyen push yok.")
                        continue

                    if cuid == ALLOWED_ID and data == "github_push_iptal":
                        _PENDING_PUSH.clear()
                        answer_callback(cqid, "❌ İptal edildi.")
                        send_msg(ALLOWED_ID, "❌ GitHub push iptal edildi.")
                        continue

                    if cuid == ALLOWED_ID and data.startswith("fb_"):
                        parts = data.split("_", 2)  # fb_iyi_konu
                        puan  = parts[1] if len(parts) > 1 else ""
                        konu  = parts[2] if len(parts) > 2 else ""
                        if puan == "daha":
                            _merak_ekle(f"{konu} hakkında daha derin araştır")
                            _feedback_kaydet_json(konu, "daha")
                            answer_callback(cqid, "🔍 Merak listesine eklendi!")
                            send_msg(ALLOWED_ID, f"🔍 <i>{konu}</i> merak listeme eklendi, yakında araştırırım.")
                        else:
                            _feedback_isle(konu, puan)
                            _feedback_kaydet_json(konu, puan)
                            emoji_map = {"iyi": "👍 Kaydettim!", "kotu": "👎 Anladım, değiştiririm."}
                            answer_callback(cqid, emoji_map.get(puan, "✅"))
                    continue

                if "message" not in update:
                    continue
                msg  = update["message"]
                cid  = msg["chat"]["id"]
                text = msg.get("text", "").strip()
                if not text:
                    continue
                if cid != ALLOWED_ID:
                    _log(f"[CHANCELLOR] Reddedildi: {cid}")
                    continue
                _log(f"[TELEGRAM_IN] [{cid}] {text[:300]}")
                executor.submit(_safe_process, cid, text)
        except KeyboardInterrupt:
            _log("[CHANCELLOR] Durduruldu.")
            break
        except Exception as e:
            consecutive_errors += 1
            # DNS / ağ hatası: exponential backoff (5s → 10s → 20s → 30s max)
            wait = min(5 * (2 ** (consecutive_errors - 1)), 30)
            _log(f"[CHANCELLOR] Döngü hatası ({consecutive_errors}): {e} — {wait}s bekleniyor")
            time.sleep(wait)

if __name__ == "__main__":
    main()
