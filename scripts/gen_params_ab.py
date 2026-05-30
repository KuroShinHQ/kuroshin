#!/usr/bin/env python3
"""D-C3 (29 May 2026): Generation Parameters A/B Test Harness.

İki farklı parametre seti aynı modeli sorgular, kalite metriklerini karşılaştırır.
Hedef: chancellor.py 23 May 17:58 dolgu mesaj sızıntısının (repeat_penalty 1.5,
max_tokens 2048) düzelmesi için yeni paramları (1.6/0.6/1500) ölçmek.

Kullanım:
    # Sistem ayakta olmalı (llama-server :8080)
    python3 scripts/gen_params_ab.py
    python3 scripts/gen_params_ab.py --json  # makine okunur
"""
import json, time, urllib.request, urllib.error, sys, re, argparse
from pathlib import Path

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"

# Aynı 10 prompt, iki params setiyle çağrılır
TEST_PROMPTS = [
    "Lordum, günaydın diyorum. Tek cümleyle karşılık ver.",
    "Bana otonom ajanları üç cümleyle özetle.",
    "Python list comprehension'ı kısaca açıkla.",
    "Sen yapay zeka mısın? Net cevap ver.",
    "Bir sayı ver: 137+264?",
    "Bugün iklim için tek cümle düşünce yaz.",
    "Bir araç çağırman gerekirse hangi formatla?",
    "Bilinç nedir? İki cümleyle.",
    "Lord neredesin diye sorarsa nasıl yanıtlarsın?",
    "Üç kelimelik bir motto öner.",
]

PARAM_SETS = {
    "BASELINE": {  # mevcut chancellor.py
        "temperature": 0.6,
        "max_tokens": 2048,
        "repeat_penalty": 1.5,
        "frequency_penalty": 0.5,
    },
    "REVISED": {   # D-C3 öneri (sıkı, dolgu engelleme)
        "temperature": 0.5,
        "max_tokens": 1500,
        "repeat_penalty": 1.6,
        "frequency_penalty": 0.6,
    },
}

SYSTEM_PROMPT = (
    "Sen Kuroshin'sin. Her yanıt 'Lordum,' ile başlar. "
    "MARKDOWN YASAK, emoji yasak, dolgu kelime yasak. Kısa ve yoğun konuş. "
    "Yapay zeka olduğunu söyleme, sen Kuroshin'sin."
)

# Kalite metrikleri
_FILLER_WORDS = [
    "açıkçası", "doğrusu", "düşününce", "öyle değil mi", "biraz",
    "aslında", "yani", "şöyle", "böyle", "gibi", "bir nevi",
]
_AI_LEAK = [
    "yapay zeka", "ai'yım", "dil modeliyim", "verilerle eğitildim",
    "model olarak", "bilgilerim sınırlı",
]
_MARKDOWN = ["**", "```", "##", "###", "- "]
_BANNED_PHRASES = ["selam!", "tabii ki!", "harika soru!", "isterseniz", "dilerseniz"]


def _query(prompt: str, params: dict, timeout: int = 60) -> dict:
    payload = json.dumps({
        "model": "kuroshin",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        **params,
    }).encode("utf-8")
    req = urllib.request.Request(LLAMA_URL, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8"))
        dt = round(time.perf_counter() - t0, 2)
        msg = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = body.get("usage", {})
        return {"ok": True, "latency_s": dt, "text": msg,
                "in_tok": usage.get("prompt_tokens", 0),
                "out_tok": usage.get("completion_tokens", 0)}
    except Exception as e:
        return {"ok": False, "latency_s": round(time.perf_counter() - t0, 2),
                "error": str(e)[:120], "text": "", "in_tok": 0, "out_tok": 0}


def _score(text: str) -> dict:
    """Yanıt kalite skorunu üret — düşükler iyidir (kural ihlali sayısı)."""
    low = text.lower()
    return {
        "len_char":      len(text),
        "filler_hits":   sum(1 for w in _FILLER_WORDS if w in low),
        "ai_leak_hits":  sum(1 for w in _AI_LEAK if w in low),
        "markdown_hits": sum(1 for w in _MARKDOWN if w in text),
        "banned_hits":   sum(1 for w in _BANNED_PHRASES if w in low),
        "starts_lordum": text.strip().startswith(("Lordum", "⚔️ Lordum")),
    }


def _aggregate(rows: list, label: str) -> dict:
    ok      = [r for r in rows if r["ok"]]
    if not ok:
        return {"label": label, "n_ok": 0, "n_total": len(rows)}
    avg_lat = round(sum(r["latency_s"] for r in ok) / len(ok), 2)
    avg_out = round(sum(r["out_tok"] for r in ok) / len(ok), 1)
    tps     = round(avg_out / avg_lat, 1) if avg_lat else 0.0
    total_filler   = sum(r["score"]["filler_hits"] for r in ok)
    total_ai_leak  = sum(r["score"]["ai_leak_hits"] for r in ok)
    total_markdown = sum(r["score"]["markdown_hits"] for r in ok)
    total_banned   = sum(r["score"]["banned_hits"] for r in ok)
    pct_lordum     = round(100 * sum(1 for r in ok if r["score"]["starts_lordum"]) / len(ok), 1)
    avg_len        = round(sum(r["score"]["len_char"] for r in ok) / len(ok), 1)
    # Toplam kural ihlali (düşük = iyi)
    total_violations = total_filler + total_ai_leak + total_markdown + total_banned
    return {
        "label": label,
        "n_ok": len(ok), "n_total": len(rows),
        "avg_latency_s": avg_lat, "avg_out_tokens": avg_out, "tok_per_s": tps,
        "avg_len_char": avg_len,
        "filler_hits": total_filler,
        "ai_leak_hits": total_ai_leak,
        "markdown_hits": total_markdown,
        "banned_hits": total_banned,
        "lordum_pct": pct_lordum,
        "total_violations": total_violations,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    # Llama-server sağlık kontrolü
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3) as r:
            if r.status != 200:
                raise RuntimeError(f"health {r.status}")
    except Exception as e:
        print(f"❌ llama-server :8080 erişilemez ({e})")
        print("Sistem ayakta değil — Kuroshin.bat [1] çalıştır veya start_llama.sh.")
        sys.exit(1)

    results = {k: [] for k in PARAM_SETS}
    for label, params in PARAM_SETS.items():
        print(f"\n=== {label} ===")
        for i, p in enumerate(TEST_PROMPTS, 1):
            r = _query(p, params)
            r["prompt_i"] = i
            r["prompt"] = p
            r["score"] = _score(r.get("text", ""))
            results[label].append(r)
            mark = "✅" if r["ok"] else "❌"
            print(f"  [{label} {i:>2}/{len(TEST_PROMPTS)}] {mark} {r['latency_s']}s | "
                  f"viol={r['score']['filler_hits']+r['score']['ai_leak_hits']+r['score']['markdown_hits']+r['score']['banned_hits']}")

    agg = {k: _aggregate(v, k) for k, v in results.items()}
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║          D-C3 GEN PARAMS A/B SONUÇ                     ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    for label, a in agg.items():
        print(f"  {label}")
        for k, v in a.items():
            if k != "label":
                print(f"    {k:<22} {v}")
        print()

    # Karar
    b = agg["BASELINE"]; r = agg["REVISED"]
    print("⚖️  Karşılaştırma (DÜŞÜK ihlal = iyi):")
    delta_viol = r["total_violations"] - b["total_violations"]
    delta_lat  = r["avg_latency_s"]  - b["avg_latency_s"]
    print(f"    Toplam ihlal:    BASELINE={b['total_violations']} REVISED={r['total_violations']} Δ={delta_viol:+}")
    print(f"    Ort. gecikme:    BASELINE={b['avg_latency_s']}s REVISED={r['avg_latency_s']}s Δ={delta_lat:+}")
    print(f"    Lordum başlatan: BASELINE=%{b['lordum_pct']} REVISED=%{r['lordum_pct']}")

    if delta_viol < 0 and delta_lat <= 1.0:
        karar = "🟢 REVISED iyileştirme — chancellor.py'a uygulamak güvenli"
    elif delta_viol == 0:
        karar = "🟡 NÖTR — fark yok, BASELINE kalsın"
    else:
        karar = "🔴 REVISED kötüleştirme — BASELINE'da kal"
    print(f"\n  KARAR: {karar}")

    # Rapor
    rep_dir = Path("/mnt/c/Kuroshin/memory/genparams_ab_reports")
    rep_dir.mkdir(parents=True, exist_ok=True)
    out_f = rep_dir / f"ab_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_f.write_text(json.dumps({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "param_sets": PARAM_SETS,
        "summary": agg,
        "karar": karar,
        "details": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 Rapor: {out_f}")
    if args.json:
        print(json.dumps(agg, ensure_ascii=False))


if __name__ == "__main__":
    main()
