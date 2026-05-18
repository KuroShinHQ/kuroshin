#!/usr/bin/env python3
"""
Kuroshin Autonomous Evaluation & Feedback Loop v1.0
Lightning.ai tarzı: test → puan → system prompt güncelle → yeniden test.

Mimari:
  1. Iron Inquisitor testleri çalıştır
  2. Başarısız/hallucination testleri topla
  3. Mevcut system prompt'u oku
  4. LLM (llama-server) aracılığıyla iyileştirilmiş prompt üret
  5. Güncellenmiş prompt'u kaydet
  6. Tekrar test et — iyileşme var mı?
  7. Telegram'a rapor gönder

Kullanım:
  python eval_feedback_loop.py [--cycles N] [--auto-apply]
"""

import subprocess, json, sys, os, re, time
from pathlib import Path
from datetime import datetime
import urllib.request, urllib.parse, socket

try:
    sys.path.insert(0, str(Path(__file__).parent))
    from skill_memory import get_skill_memory
    _skill_mem = get_skill_memory()
except Exception:
    _skill_mem = None

# --- Paths ---
BASE          = Path(r"C:\Kuroshin")
INQUISITOR    = Path(__file__).parent / "inquisitor.py"
SUITE         = Path(__file__).parent / "test_suite.json"
PROMPT_FILE   = BASE / "config" / "system_prompt.md"
PROMPT_BACKUP = BASE / "config" / "system_prompt_backups"
REPORT_DIR    = Path(__file__).parent / "reports"
LLAMA_URL     = "http://127.0.0.1:8080/v1/chat/completions"
LITELLM_URL   = "http://127.0.0.1:6000/v1/chat/completions"

MAX_CYCLES    = 3
IMPROVE_THRESHOLD = 0.1  # en az %10 iyileşme olmazsa dur

# --- IPv4 forcing ---
_orig_gai = socket.getaddrinfo
def _ipv4_only(host, port, family=0, *a, **kw):
    return _orig_gai(host, port, socket.AF_INET, *a, **kw)

def _tg_token():
    try:
        src = (BASE / "agents" / "kuroshin_chancellor.py").read_text(encoding="utf-8", errors="ignore")
        t   = re.search(r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']', src)
        c   = re.search(r'CHAT_ID\s*=\s*["\']([^"\']+)["\']', src)
        return (t.group(1) if t else None), (c.group(1) if c else None)
    except Exception:
        return None, None

def send_telegram(msg: str):
    socket.getaddrinfo = _ipv4_only
    try:
        token, chat_id = _tg_token()
        if not token:
            return
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=10)
    except Exception as e:
        print(f"[TG] {e}")
    finally:
        socket.getaddrinfo = _orig_gai

# --- Run Inquisitor ---
def run_inquisitor() -> tuple[list[dict], float]:
    """Returns (results, score_pct)"""
    proc = subprocess.run(
        [sys.executable, str(INQUISITOR), "--suite", str(SUITE)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600
    )
    # Find latest JSON report
    if not REPORT_DIR.exists():
        return [], 0.0
    reports = sorted(REPORT_DIR.glob("inquisitor_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return [], 0.0
    results = json.loads(reports[0].read_text(encoding="utf-8"))
    total_w = sum(r.get("weight", 1.0) for r in results)
    earned  = sum(r.get("score",  0.0) for r in results)
    pct     = round(100 * earned / total_w, 1) if total_w else 0.0
    return results, pct

# --- Read current system prompt ---
def get_system_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    # Try to find it in openclaude config
    oc_dir = BASE / "openclaude-main"
    for candidate in oc_dir.rglob("CLAUDE.md"):
        return candidate.read_text(encoding="utf-8")
    return ""

def save_system_prompt(content: str):
    PROMPT_BACKUP.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Backup current
    if PROMPT_FILE.exists():
        backup = PROMPT_BACKUP / f"system_prompt_{ts}.md"
        backup.write_text(PROMPT_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_FILE.write_text(content, encoding="utf-8")
    print(f"[EVAL] System prompt kaydedildi: {PROMPT_FILE}")

# --- LLM-based prompt improvement ---
def improve_prompt_with_llm(current_prompt: str, failed_tests: list[dict]) -> str:
    """Ask llama-server to improve the system prompt based on failures."""
    failure_summary = "\n".join([
        f"- [{r['status']}] {r['id']} ({r['tool']}): {r['note']}"
        for r in failed_tests
    ])

    # Skill memory'den başarılı pattern'leri çek
    skill_context = ""
    if _skill_mem:
        try:
            failed_tools = list(set(r.get("tool", "") for r in failed_tests if r.get("tool")))
            skill_context = _skill_mem.build_context_for_prompt(failed_tools)
        except Exception:
            pass

    user_msg = f"""Aşağıda bir AI sisteminin mevcut system prompt'u ve başarısız test sonuçları var.
Başarısız testlere bakarak system prompt'u iyileştir. Araç kullanım örnekleri ekle, hallucination önle.

=== MEVCUT SYSTEM PROMPT (ilk 2000 karakter) ===
{current_prompt[:2000]}

{f"=== GEÇMİŞ BAŞARILI PATTERN'LER (Skill Memory) ==={chr(10)}{skill_context}" if skill_context else ""}

=== BAŞARISIZ TESTLER ===
{failure_summary}

=== GÖREV ===
System prompt'a eklenecek yeni kuralları yaz. Sadece ekleme/değişiklik bölümlerini yaz.
Formatı koru, kısa ve etkili ol. Türkçe yaz."""

    payload = {
        "model": "gemma4",
        "messages": [{"role": "user", "content": user_msg}],
        "max_tokens": 1024,
        "temperature": 0.3,
    }

    headers = {"Content-Type": "application/json", "Authorization": "Bearer kuroshin-secret"}

    for url in [LLAMA_URL, LITELLM_URL]:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers=headers,
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=60)
            data = json.loads(resp.read())
            suggestion = data["choices"][0]["message"]["content"].strip()
            print(f"[EVAL] LLM öneri ({len(suggestion)} karakter) alındı")
            return suggestion
        except Exception as e:
            print(f"[EVAL] LLM bağlantısı başarısız ({url}): {e}")

    return ""

# --- Score tracker for continuous improvement ---
def load_score_history() -> list[dict]:
    history_file = REPORT_DIR / "score_history.json"
    if history_file.exists():
        return json.loads(history_file.read_text(encoding="utf-8"))
    return []

def save_score_history(history: list[dict]):
    REPORT_DIR.mkdir(exist_ok=True)
    history_file = REPORT_DIR / "score_history.json"
    history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

def record_score(cycle: int, score_pct: float, applied_changes: bool):
    history = load_score_history()
    history.append({
        "ts":             datetime.now().isoformat(),
        "cycle":          cycle,
        "score_pct":      score_pct,
        "applied_changes": applied_changes,
    })
    save_score_history(history)

# --- Main Feedback Loop ---
def main():
    auto_apply = "--auto-apply" in sys.argv
    cycles = MAX_CYCLES
    for i, a in enumerate(sys.argv[1:]):
        if a == "--cycles" and i+2 < len(sys.argv):
            cycles = int(sys.argv[i+2])

    print(f"[EVAL] Iron Inquisitor Eval Loop başlatılıyor ({cycles} döngü, auto_apply={auto_apply})")
    send_telegram(f"⚔️ <b>Iron Inquisitor Eval Loop</b> başlıyor ({cycles} döngü)")

    prev_score = None
    history = load_score_history()

    for cycle in range(1, cycles + 1):
        print(f"\n{'='*60}")
        print(f"[EVAL] DÖNGÜ {cycle}/{cycles}")
        print(f"{'='*60}")

        # Run tests
        send_telegram(f"🔬 Döngü {cycle}/{cycles} — testler çalıştırılıyor...")
        results, score_pct = run_inquisitor()

        if not results:
            print("[EVAL] Test sonuçları alınamadı, çıkılıyor")
            send_telegram("❌ Test sonuçları alınamadı")
            break

        print(f"[EVAL] Skor: %{score_pct}")
        record_score(cycle, score_pct, False)

        # Check improvement
        if prev_score is not None:
            delta = score_pct - prev_score
            if delta < IMPROVE_THRESHOLD * 100:
                print(f"[EVAL] İyileşme yok (delta={delta:.1f}%), durduruluyor")
                send_telegram(f"⏹️ İyileşme duraklatıldı. Delta: {delta:+.1f}%")
                break

        prev_score = score_pct

        # Get failures
        failed = [r for r in results if r["status"] in ("FAIL", "HALLUCINATION", "TIMEOUT")]
        if not failed:
            msg = f"✅ <b>Tüm testler geçti!</b> Skor: %{score_pct}\n🏆 System prompt optimize — görev tamamlandı."
            print(f"[EVAL] {msg}")
            send_telegram(msg)
            break

        print(f"[EVAL] {len(failed)} başarısız test, LLM'den öneri alınıyor...")
        current_prompt = get_system_prompt()
        suggestion = improve_prompt_with_llm(current_prompt, failed)

        if suggestion and auto_apply:
            new_prompt = current_prompt + f"\n\n<!-- INQUISITOR PATCH {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n{suggestion}"
            save_system_prompt(new_prompt)
            record_score(cycle, score_pct, True)

            tg_msg = (
                f"🔧 <b>Döngü {cycle} — Prompt Güncellendi</b>\n"
                f"📊 Skor: %{score_pct} | Başarısız: {len(failed)}\n"
                f"💡 Eklenen kural sayısı: {suggestion.count(chr(10))+1}\n"
                f"🔄 Sonraki döngü başlıyor..."
            )
            send_telegram(tg_msg)
            time.sleep(5)
        elif suggestion:
            # Report only — don't apply automatically
            REPORT_DIR.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            suggestion_file = REPORT_DIR / f"prompt_suggestion_{ts}.md"
            suggestion_file.write_text(suggestion, encoding="utf-8")
            print(f"[EVAL] Öneri kaydedildi (--auto-apply olmadan uygulanmadı): {suggestion_file}")

            tg_msg = (
                f"📋 <b>Döngü {cycle} — Öneri Hazır</b>\n"
                f"📊 Skor: %{score_pct} | Başarısız: {len(failed)}\n"
                f"💡 Öneri dosyası: reports/prompt_suggestion_{ts}.md\n"
                f"⚠️ Otomatik uygulamak için --auto-apply ekle"
            )
            send_telegram(tg_msg)
            break
        else:
            print("[EVAL] LLM'den öneri alınamadı")
            send_telegram(f"⚠️ Döngü {cycle}: LLM yanıt vermedi, döngü durduruldu")
            break

    # Final summary
    history = load_score_history()
    if len(history) >= 2:
        first = history[0]["score_pct"]
        last  = history[-1]["score_pct"]
        delta = last - first
        send_telegram(
            f"⚔️ <b>Eval Loop Tamamlandı</b>\n"
            f"📈 İlk skor: %{first} → Son skor: %{last} ({delta:+.1f}%)\n"
            f"🔄 {len(history)} döngü tamamlandı"
        )

if __name__ == "__main__":
    main()
