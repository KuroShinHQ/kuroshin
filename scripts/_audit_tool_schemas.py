#!/usr/bin/env python3
"""
Tool Şema Denetçisi (31 May 2026)
==================================
chancellor.py TOOLS şemalarını handler kullanımına karşı statik denetler.
Amaç: system_info-sınıfı gizli bug'ları yakalamak.

İki kusur tipi:
  [E13-RISK]  Bir param 'required' listesinde AMA handler'da args.get("p", DEFAULT)
              ile default'u var → model {} veya p'siz çağırırsa şema reddeder (E-13),
              ama handler aslında onsuz çalışabilirdi. (system_info/'konu' buydu.)
  [KEYERR]    Handler args["p"] (default'suz subscript) kullanıyor AMA p 'required'
              değil → model p'siz çağırırsa KeyError riski.

Salt-okuma, yan etkisiz (chancellor'ı import ETMEZ — AST ile parse eder).
Çıkış 0 = kusur yok.
"""
from __future__ import annotations
import ast
import re
import sys
from pathlib import Path

CHANCELLOR = Path("/mnt/c/Kuroshin/agents/kuroshin_chancellor.py")
src = CHANCELLOR.read_text(encoding="utf-8")
tree = ast.parse(src)

# 1) TOOLS listesini AST ile guvenli cikar
tools = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "TOOLS":
                try:
                    tools = ast.literal_eval(node.value)
                except Exception as e:
                    print(f"TOOLS literal_eval hatasi: {e}")
                    sys.exit(2)
if tools is None:
    print("TOOLS bulunamadi"); sys.exit(2)

# 2) Her tool icin handler govdesini izole et
#    Handler isaretleri: name == "X"  (if/elif bloklari)
def handler_body(tool_name: str) -> str:
    # name == "tool"  baslangici
    m = re.search(r'name\s*==\s*[\'"]' + re.escape(tool_name) + r'[\'"]', src)
    if not m:
        return ""
    start = m.start()
    # bir sonraki  name ==  veya  name in  blokuna kadar
    nxt = re.search(r'\n\s*elif\s+name\s*(==|in)\s', src[start + 5:])
    end = start + 5 + nxt.start() if nxt else min(start + 2500, len(src))
    return src[start:end]

# İncelendi (31 May 2026): cekirdek-eylem parametreleri (islem/path/subreddit/mesaj).
# Model bunlari dogal olarak saglar; zorunlu olmalari DOGRU tasarim. Default sadece savunmaci.
# system_info/'konu' bunlardan FARKLIYDI (info-tool + rafinasyon param) → tek gercek bug, duzeltildi.
# Yeni bir tool system_info-sinifi bug eklerse (whitelist disi) audit onu flag'ler.
_REVIEWED_BY_DESIGN = {
    ("reddit_tool", "islem"), ("reddit_read", "subreddit"), ("write_file", "path"),
    ("model_switch", "islem"), ("memory_manage", "islem"), ("reminder", "mesaj"),
    ("github", "islem"), ("gemini", "islem"), ("aktivite_gunluk", "islem"),
    ("goal_manage", "islem"), ("task_status", "islem"),
}

findings = []
audited = 0
for entry in tools:
    fn = entry.get("function", {})
    name = fn.get("name", "?")
    params = fn.get("parameters", {}) or {}
    required = params.get("required", []) or []
    props = list((params.get("properties", {}) or {}).keys())
    body = handler_body(name)
    audited += 1
    if not body:
        findings.append(("NO_HANDLER", name, "handler govdesi bulunamadi (run_tool disinda olabilir)"))
        continue
    # [E13-RISK] required param handler'da ANLAMLI (bos olmayan) default'lu mu?
    #   args.get("p", "")  → sentinel, handler reddeder → param gercekten zorunlu (FLAG ETME)
    #   args.get("p", "hepsi") → anlamli fallback → param efektif opsiyonel (system_info bug'i) → FLAG
    for r in required:
        m = re.search(r'args\.get\(\s*[\'"]' + re.escape(r) + r'[\'"]\s*,\s*([^)]+?)\s*\)', body)
        if not m:
            continue
        default_expr = m.group(1).strip()
        # Anlamli default: bos-olmayan string literal ('x'/"x") veya sayi
        meaningful = bool(re.fullmatch(r'[\'"][^\'"]+[\'"]', default_expr)) or bool(re.fullmatch(r'\d+', default_expr))
        sentinel = default_expr in ('""', "''", 'None', '[]', '{}', '""', "''")
        if meaningful and not sentinel and (name, r) not in _REVIEWED_BY_DESIGN:
            findings.append(("E13-RISK", name, f"'{r}' required AMA handler default={default_expr} (anlamli fallback) → param efektif opsiyonel, E-13 garantili — YENI, incele!"))
    # [KEYERR] default'suz subscript ama required degil
    for p in props:
        if p in required:
            continue
        if re.search(r'args\[\s*[\'"]' + re.escape(p) + r'[\'"]\s*\]', body):
            findings.append(("KEYERR", name, f"handler args['{p}'] (default'suz) AMA '{p}' required degil → KeyError riski"))

# 3) Rapor
print(f"=== TOOL SEMA DENETIMI: {audited} tool denetlendi ===")
e13 = [f for f in findings if f[0] == "E13-RISK"]
keyerr = [f for f in findings if f[0] == "KEYERR"]
nohand = [f for f in findings if f[0] == "NO_HANDLER"]
for kind, name, msg in findings:
    print(f"  [{kind}] {name}: {msg}")
print(f"\nSONUC: E13-RISK={len(e13)} | KEYERR={len(keyerr)} | NO_HANDLER={len(nohand)}")
# NO_HANDLER bilgi amacli (router'a ozel olabilir), E13/KEYERR gercek bug
critical = len(e13) + len(keyerr)
print("DURUM:", "TEMIZ" if critical == 0 else f"{critical} GERCEK KUSUR")
sys.exit(0 if critical == 0 else 1)
