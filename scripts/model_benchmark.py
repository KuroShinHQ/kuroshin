#!/usr/bin/env python3
"""
Kuroshin Model Benchmark — Gemma4 vs Qwen2.5-Coder-1.5B
Kategoriler: Türkçe anlama, Araç çağrısı, Kod üretimi, Matematik, Hız
"""
import time
import json
import requests
from pathlib import Path

MODELS = {
    "Gemma4-E4B-Q4KM": "http://127.0.0.1:8080/v1/chat/completions",
    "Qwen2.5-Coder-1.5B": "http://127.0.0.1:8081/v1/chat/completions",
}

TESTS = [
    {
        "kategori": "Türkçe Anlama",
        "soru": "Aşağıdaki paragrafı özetle ve ana fikri tek cümlede söyle:\n\nYapay zeka, insan zekasını taklit eden bilgisayar sistemleri olarak tanımlanır. Makine öğrenimi, derin öğrenme ve doğal dil işleme gibi alt dalları vardır. Son yıllarda büyük dil modelleri sayesinde yapay zeka günlük hayata hızla girmiştir.",
        "beklenen": "özet + ana fikir",
        "max_tokens": 150,
    },
    {
        "kategori": "Kod Üretimi",
        "soru": "Python'da bir liste içindeki tekrar eden elemanları silen ve orijinal sıralamayı koruyan fonksiyon yaz. Sadece kodu ver.",
        "beklenen": "def fonksiyon",
        "max_tokens": 200,
    },
    {
        "kategori": "Matematik",
        "soru": "Bir trenin hızı 120 km/s ve 3.5 saatte kat ettiği mesafe kaç km? Sadece sayı ver.",
        "beklenen": "420",
        "max_tokens": 50,
    },
    {
        "kategori": "Mantık/Çıkarım",
        "soru": "Ali'nin 3 kardeşi var. Her kardeşin 2 çocuğu var. Ali'nin kaç yeğeni var? Sadece sayı ver.",
        "beklenen": "6",
        "max_tokens": 30,
    },
    {
        "kategori": "Yaratıcı Yazma",
        "soru": "Yapay zekanın insanlığın geleceğini nasıl şekillendireceğini 2 cümlede anlat.",
        "beklenen": "2 cümle",
        "max_tokens": 120,
    },
    {
        "kategori": "İngilizce Anlama",
        "soru": "What is the capital of Turkey? Answer in one word.",
        "beklenen": "Ankara",
        "max_tokens": 20,
    },
    {
        "kategori": "Araç/JSON Formatı",
        "soru": 'Aşağıdaki JSON şemasına göre örnek veri üret:\n{"name": string, "age": integer, "city": string}\nSadece JSON ver.',
        "beklenen": "json",
        "max_tokens": 80,
    },
]

def ask_model(url, soru, max_tokens=200):
    t0 = time.time()
    try:
        r = requests.post(url, json={
            "model": "local",
            "messages": [{"role": "user", "content": soru}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }, timeout=60)
        elapsed = time.time() - t0
        if r.ok:
            data = r.json()
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or msg.get("reasoning") or "").strip()
            usage = data.get("usage", {})
            tokens = usage.get("completion_tokens", 0)
            tok_s = round(tokens / elapsed, 1) if elapsed > 0 else 0
            return content, elapsed, tok_s
        else:
            return f"HTTP {r.status_code}", time.time() - t0, 0
    except Exception as e:
        return f"HATA: {e}", time.time() - t0, 0

def run_benchmark():
    results = {}
    for model_name, url in MODELS.items():
        print(f"\n{'='*60}")
        print(f"MODEL: {model_name}")
        print(f"{'='*60}")
        model_results = []
        for test in TESTS:
            print(f"\n[{test['kategori']}]")
            print(f"Soru: {test['soru'][:80]}...")
            yanit, sure, tok_s = ask_model(url, test["soru"], test["max_tokens"])
            print(f"Yanıt: {yanit[:150]}")
            print(f"Süre: {sure:.1f}s | Hız: {tok_s} tok/s")
            model_results.append({
                "kategori": test["kategori"],
                "yanit": yanit[:300],
                "sure": round(sure, 2),
                "tok_s": tok_s,
                "beklenen": test["beklenen"],
            })
        results[model_name] = model_results

    return results

if __name__ == "__main__":
    print("Kuroshin Model Benchmark başlıyor...")
    results = run_benchmark()
    out = Path("/mnt/c/Kuroshin/reports/model_benchmark_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n\nSonuçlar kaydedildi: {out}")
    print(json.dumps(results, ensure_ascii=False, indent=2)[:2000])
