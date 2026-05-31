#!/usr/bin/env python3
"""
Kalite Düzeltme Doğrulaması (31 May 2026)
Telegram çıktı kalitesi için yapılan 2 deterministik düzeltmeyi kanıtlar:

  FIX-1: system_info tool şeması 'konu'yu ZORUNLU sanıyordu → tool tamamen kırıktı
         (E-13 INVALID_TOOL_ARGS döngüsü). Handler zaten konu='hepsi' default'u
         kullandığından required=[] olmalı.
  FIX-2: Yanıt finalizasyonunda yetim variation selector (U+FE0E/FE0F) kalıyordu
         (örn. "Lordum, <VS> Merhametli"). Boşluk/satır başı sonrası VS yetimdir;
         geçerli emojide (⚔️ = U+2694 U+FE0F) VS baza bitişik olduğu için korunur.

Çalıştır:
  python3 /mnt/c/Kuroshin/scripts/_verify_quality_fixes.py
Çıkış kodu 0 = tüm testler PASS.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

CHANCELLOR = Path("/mnt/c/Kuroshin/agents/kuroshin_chancellor.py")

# chancellor.py finalizasyonundaki yetim-VS stripin AYNISI
_VS_STRIP = re.compile("(?:^|(?<=\\s))[︎️]+\\s*")
def strip_orphan_vs(s: str) -> str:
    return _VS_STRIP.sub("", s)

SWORD = "⚔️"  # ⚔️
VS = "️"

results = []
def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))

# ── FIX-2 birim testleri ─────────────────────────────
t1_in = f"{SWORD} Lordum, {VS} Merhametli kuroshin_user, meraba"
t1_out = strip_orphan_vs(t1_in)
check("VS-orphan-removed", VS + " Merh" not in t1_out and "Lordum, Merhametli" in t1_out, repr(t1_out))
check("VS-sword-preserved", t1_out.startswith(f"{SWORD} Lordum,"), repr(t1_out[:14]))

# Yalın emoji (baza bitişik VS) bozulmamalı
emoji_in = f"{SWORD} Lordum, harika"
check("VS-clean-noop", strip_orphan_vs(emoji_in) == emoji_in, repr(strip_orphan_vs(emoji_in)))

# Satır başındaki yetim VS
ln_in = f"{VS} test"
check("VS-leading-removed", strip_orphan_vs(ln_in) == "test", repr(strip_orphan_vs(ln_in)))

# ── FIX-1 + FIX-2 kaynak doğrulaması ─────────────────
src = CHANCELLOR.read_text(encoding="utf-8")

# system_info şeması bloğunu izole et (sonraki tool tanımına kadar)
idx = src.find('"name": "system_info"')
nxt = src.find('"name":', idx + 10) if idx != -1 else -1
seg = src[idx: nxt] if (idx != -1 and nxt != -1) else (src[idx: idx + 1200] if idx != -1 else "")
check("system_info-found", idx != -1)
check("system_info-not-required-konu", '"required": ["konu"]' not in seg, "eski hatali required kalmamali")
check("system_info-required-empty", '"required": []' in seg, "required=[] olmali")

# Yetim-VS strip satiri kaynakta var mi (literal VS bracket + yorum)
check("vs-strip-line-present", "[︎️]+" in src and "variation selector" in src.lower())

# ── Rapor ────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"=== KALITE FIX DOGRULAMA: {passed}/{total} ===")
for name, ok, detail in results:
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name}" + (f"  -> {detail}" if detail else ""))
print(f"SONUC: {'PASS' if passed == total else 'FAIL'}")
sys.exit(0 if passed == total else 1)
