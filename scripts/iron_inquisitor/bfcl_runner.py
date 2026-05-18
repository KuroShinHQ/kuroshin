#!/usr/bin/env python3
"""
Kuroshin BFCL Runner v1.0
Berkeley Function Calling Leaderboard testlerini yerel Gemma4 üzerinde çalıştırır.
Iron Inquisitor ile entegre çalışır.

Kullanım:
  python3 bfcl_runner.py --dry-run         # sistem kontrolü
  python3 bfcl_runner.py --category simple # basit testler
  python3 bfcl_runner.py                   # tüm temel kategoriler
"""

import sys
import json
import subprocess
import time
import urllib.request
import re
from pathlib import Path
from datetime import datetime

VENV_PYTHON   = "/root/kuroshin/venv/bin/python3"
LLAMA_URL     = "http://127.0.0.1:8080/v1/chat/completions"
REPORT_DIR    = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# Yerel BFCL test senaryoları (BFCL'in resmi formatına uygun minimal versiyon)
# Tam BFCL resmi testler için model endpoint kaydı gerekir,
# bu runner kendi ürettiği tool-call testlerini kullanır.
BFCL_LOCAL_TESTS = [
    {
        "id": "bfcl-simple-01",
        "category": "simple",
        "prompt": "Hava durumunu öğrenmek istiyorum. get_weather fonksiyonunu çağır, location='Istanbul'",
        "available_tools": [
            {"name": "get_weather", "description": "Hava durumu bilgisi al",
             "parameters": {"type": "object", "properties": {
                 "location": {"type": "string", "description": "Şehir adı"}
             }, "required": ["location"]}}
        ],
        "expected_tool": "get_weather",
        "expected_params": {"location": "Istanbul"},
    },
    {
        "id": "bfcl-simple-02",
        "category": "simple",
        "prompt": "1 USD kaç TL eder? convert_currency fonksiyonunu kullan, from_currency='USD', to_currency='TRY', amount=1",
        "available_tools": [
            {"name": "convert_currency", "description": "Para birimi çevir",
             "parameters": {"type": "object", "properties": {
                 "from_currency": {"type": "string"},
                 "to_currency":   {"type": "string"},
                 "amount":        {"type": "number"},
             }, "required": ["from_currency", "to_currency", "amount"]}}
        ],
        "expected_tool": "convert_currency",
        "expected_params": {"from_currency": "USD", "to_currency": "TRY"},
    },
    {
        "id": "bfcl-irrelevance-01",
        "category": "irrelevance",
        "prompt": "Merhaba, nasılsın?",
        "available_tools": [
            {"name": "get_weather", "description": "Hava durumu al",
             "parameters": {"type": "object", "properties": {
                 "location": {"type": "string"}
             }, "required": ["location"]}}
        ],
        "expected_tool": None,  # Araç çağırılmamalı
    },
    {
        "id": "bfcl-multiple-01",
        "category": "multiple",
        "prompt": "İstanbul ve Ankara'nın hava durumunu öğren. Her ikisi için ayrı get_weather çağrısı yap.",
        "available_tools": [
            {"name": "get_weather", "description": "Hava durumu al",
             "parameters": {"type": "object", "properties": {
                 "location": {"type": "string"}
             }, "required": ["location"]}}
        ],
        "expected_tool": "get_weather",
        "expected_multiple": True,
    },
]


def call_llama(prompt: str, tools: list) -> dict:
    """Gemma4'e araç listesiyle birlikte prompt gönder."""
    payload = {
        "model": "gemma4",
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "function", "function": t} for t in tools],
        "tool_choice": "auto",
        "max_tokens": 512,
        "temperature": 0.1,
    }
    try:
        req = urllib.request.Request(
            LLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer kuroshin-secret"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def evaluate_response(test: dict, response: dict) -> dict:
    """BFCL tarzı AST değerlendirme — araç adı ve parametre doğruluğu."""
    if "error" in response:
        return {"status": "ERROR", "score": 0.0, "note": response["error"]}

    # Model yanıtından tool_calls çıkar
    choices = response.get("choices", [])
    tool_calls = []
    text_response = ""
    if choices:
        msg = choices[0].get("message", {})
        tool_calls = msg.get("tool_calls", [])
        text_response = msg.get("content", "") or ""

    expected_tool = test.get("expected_tool")
    expected_params = test.get("expected_params", {})
    expect_multiple = test.get("expected_multiple", False)

    # irrelevance testi: araç çağırılmamalı
    if expected_tool is None:
        if not tool_calls:
            return {"status": "PASS", "score": 1.0, "note": "Doğru: araç çağırılmadı"}
        else:
            called = tool_calls[0].get("function", {}).get("name", "")
            return {"status": "FAIL", "score": 0.0,
                    "note": f"Hatalı araç çağrısı: {called} (beklenen: yok)"}

    if not tool_calls:
        # Metin yanıtta araç adı geçiyor mu?
        if expected_tool.lower() in text_response.lower():
            return {"status": "PARTIAL", "score": 0.3,
                    "note": "Araç adı metinde var ama tool_call formatında değil"}
        return {"status": "FAIL", "score": 0.0, "note": "Araç çağrısı yapılmadı"}

    # Multiple test: en az 2 çağrı
    if expect_multiple and len(tool_calls) < 2:
        return {"status": "PARTIAL", "score": 0.5,
                "note": f"Tek çağrı yapıldı, birden fazla bekleniyor"}

    # İlk tool_call değerlendir
    first_call = tool_calls[0]
    func = first_call.get("function", {})
    called_name = func.get("name", "")
    try:
        called_args = json.loads(func.get("arguments", "{}"))
    except Exception:
        called_args = {}

    # Araç adı doğru mu?
    if called_name != expected_tool:
        return {"status": "FAIL", "score": 0.2,
                "note": f"Yanlış araç: {called_name} (beklenen: {expected_tool})"}

    # Parametre kontrolü
    param_score = 1.0
    missing = []
    wrong = []
    for k, v in expected_params.items():
        if k not in called_args:
            missing.append(k)
            param_score -= 0.2
        elif str(called_args[k]).lower() != str(v).lower():
            wrong.append(f"{k}={called_args[k]} (beklenen {v})")
            param_score -= 0.1

    if missing or wrong:
        note = ""
        if missing: note += f"Eksik param: {missing}. "
        if wrong:   note += f"Yanlış param: {wrong}."
        return {"status": "PARTIAL", "score": max(0.1, param_score),
                "note": note.strip()}

    return {"status": "PASS", "score": 1.0, "note": "Araç ve parametreler doğru"}


def run_bfcl(category: str = "all", dry_run: bool = False) -> dict:
    """BFCL testlerini çalıştır ve skor döndür."""
    tests = BFCL_LOCAL_TESTS
    if category != "all":
        tests = [t for t in tests if t["category"] == category]

    if not tests:
        return {"error": f"Kategori bulunamadı: {category}"}

    if dry_run:
        print(f"[BFCL] DRY-RUN: {len(tests)} test hazır, llama-server kontrol ediliyor...")
        try:
            urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3)
            print("[BFCL] llama-server: OK")
        except Exception:
            print("[BFCL] llama-server: ULAŞILAMIYOR")
        return {"dry_run": True, "test_count": len(tests)}

    results = []
    for test in tests:
        print(f"  [{test['id']}] çalıştırılıyor...", end=" ", flush=True)
        t_start = time.time()
        response = call_llama(test["prompt"], test["available_tools"])
        elapsed = round(time.time() - t_start, 1)
        result = evaluate_response(test, response)
        result.update({"id": test["id"], "category": test["category"], "elapsed": elapsed})
        results.append(result)
        icon = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "ERROR": "💥"}.get(result["status"], "?")
        print(f"{icon} {result['status']} ({elapsed}s) — {result['note'][:60]}")

    # Özet
    total = len(results)
    passes = sum(1 for r in results if r["status"] == "PASS")
    score_pct = round(100 * sum(r["score"] for r in results) / total, 1) if total else 0

    summary = {
        "ts":        datetime.now().isoformat(),
        "category":  category,
        "total":     total,
        "pass":      passes,
        "score_pct": score_pct,
        "results":   results,
    }

    # Kaydet
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORT_DIR / f"bfcl_{ts}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[BFCL] Skor: %{score_pct} ({passes}/{total} PASS) — Rapor: {out.name}")

    return summary


if __name__ == "__main__":
    dry_run  = "--dry-run" in sys.argv
    category = "all"
    for i, a in enumerate(sys.argv[1:]):
        if a == "--category" and i + 2 < len(sys.argv):
            category = sys.argv[i + 2]

    run_bfcl(category=category, dry_run=dry_run)
