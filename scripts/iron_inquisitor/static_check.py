#!/usr/bin/env python3
"""
Iron Inquisitor — Statik Kod Analizi (yeni özellik doğrulama)
Çalıştır: python3 static_check.py
"""
from pathlib import Path
import ast, sys

BASE = Path(r"C:\Kuroshin") if (Path(r"C:\Kuroshin")).exists() else Path("/mnt/c/Kuroshin")

def read(rel):
    try:
        return (BASE / rel).read_text(encoding="utf-8")
    except Exception as e:
        return f"__READ_ERROR__: {e}"

results = []

def check(tid, cond, note_ok, note_fail, weight=1.0):
    if cond:
        results.append((tid, "PASS", note_ok, weight))
    else:
        results.append((tid, "FAIL", note_fail, weight))

ch  = read("agents/kuroshin_chancellor.py")
il  = read("soul/idle_loop.py")
sm  = read("scripts/switch_model.py")
bat = read("Kuroshin.bat")
mcp = read("openclaude-main/.mcp.wsl.json") or read("openclaude-main/.mcp.json")

# --- Syntax kontrolleri ---
for rel in ["agents/kuroshin_chancellor.py", "scripts/switch_model.py",
            "soul/idle_loop.py", "soul/dream_engine.py"]:
    content = read(rel)
    try:
        ast.parse(content)
        check(f"syntax-{rel.split('/')[-1]}", True, f"Syntax OK", "Parse hatası")
    except SyntaxError as e:
        check(f"syntax-{rel.split('/')[-1]}", False, "", f"SyntaxError: {e}")

# --- ChromaDB in-process ---
check("chroma-inprocess", "PersistentClient" in ch and "_get_chroma_col" in ch,
      "PersistentClient + _get_chroma_col mevcut",
      "In-process ChromaDB eksik — hâlâ HTTP kullanıyor")

check("chroma-save", "_save_to_chroma" in ch and "col.add(" in ch,
      "col.add() ile kayıt mevcut",
      "_save_to_chroma hâlâ requests.post kullanıyor")

# --- Model switch ---
check("model-switch-tool", '"model_switch"' in ch,
      "model_switch TOOLS listesinde", "TOOLS'da model_switch yok")

check("model-switch-handler", "elif name == \"model_switch\":" in ch and "gecis" in ch,
      "model_switch handler mevcut", "handler eksik")

check("model-switch-script", "def list_models" in sm and "def switch_model" in sm,
      "list_models + switch_model fonksiyonları var",
      "switch_model.py fonksiyonları eksik")

check("model-history", "model_history" in sm and "model_history.json" in sm,
      "model_history.json kayıt mevcut", "model_history yok")

# --- PDF reader ---
check("pdf-reader-tool", '"pdf_reader"' in ch,
      "pdf_reader TOOLS listesinde", "pdf_reader yok")

check("pdf-reader-handler", 'elif name == "pdf_reader":' in ch and "fitz" in ch,
      "pdf_reader handler + PyMuPDF mevcut", "handler eksik")

# --- Proaktif sohbet ---
check("proaktif-func", "def check_proaktif_sohbet" in il,
      "check_proaktif_sohbet() tanımlı", "fonksiyon yok")

check("proaktif-online", "_kullanici_online_mu" in il,
      "_kullanici_online_mu() mevcut", "online check yok")

check("proaktif-profil", "ilgi_profili" in il and "_kaydet_ilgi_profili" in il,
      "ilgi_profili kayıt mevcut", "profil sistemi yok")

check("proaktif-run", "check_proaktif_sohbet()" in il,
      "check_proaktif_sohbet() run() içinde çağrılıyor", "run() içinde çağrı yok")

# --- Bat menü ---
check("bat-model-menu", "MODEL_SWITCH" in bat and "[8]" in bat,
      "[8] MODEL_SWITCH bat menüsünde", "bat menüsü güncellenmemiş")

check("bat-do-switch", ":DO_SWITCH" in bat and "switch_model.py" in bat,
      ":DO_SWITCH + switch_model.py bat'ta mevcut", "DO_SWITCH yok")

# --- Slash komutlar ---
check("slash-model", "/model_list" in ch and "/model_switch" in ch,
      "/model_list + /model_switch slash komutları var", "slash komutlar yok")

check("slash-bat", "/bat_stop" in ch and "/bat" in ch,
      "/bat + /bat_stop mevcut", "bat slash komutları yok")

# --- Yardımcı araçlar ---
check("reminder-tool", '"reminder"' in ch and "_hatirlatici" in ch,
      "reminder tool + _hatirlatici() mevcut", "reminder eksik")

check("self-update-tool", '"self_update"' in ch and "mood_sifirla" in ch,
      "self_update tool mevcut", "self_update eksik")

check("memory-manage-tool", '"memory_manage"' in ch and "col.delete(" in ch,
      "memory_manage (in-process) mevcut", "memory_manage eksik veya hâlâ HTTP")

check("chroma-search-tool", '"chroma_search"' in ch and "col.query(" in ch,
      "chroma_search (in-process) mevcut", "chroma_search eksik")

# --- SYSTEM_PROMPT ---
check("system-prompt-tools", "model_switch" in ch and "pdf_reader" in ch and "chroma_search" in ch,
      "SYSTEM_PROMPT araç kuralları güncel", "Araç kuralları eksik")

# --- Sonuçlar ---
passes = [r for r in results if r[1] == "PASS"]
fails  = [r for r in results if r[1] == "FAIL"]
total_weight = sum(r[3] for r in results)
earned = sum(r[3] for r in results if r[1] == "PASS")
pct = round(100 * earned / total_weight, 1)

print()
print("=" * 60)
print("  Iron Inquisitor — Statik Kod Analizi")
print("  Yeni Özellik Doğrulama")
print("=" * 60)

for tid, status, note, _ in results:
    icon = "✅" if status == "PASS" else "❌"
    print(f"  {icon} [{tid}]")
    print(f"       {note}")

print()
print(f"  Sonuç: {len(passes)}/{len(results)} PASS — {pct}%")
if fails:
    print(f"  Başarısız: {', '.join(r[0] for r in fails)}")
print("=" * 60)
sys.exit(0 if not fails else 1)
