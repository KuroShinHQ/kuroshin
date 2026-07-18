#!/usr/bin/env python3
"""
Kuroshin Autonomous Benchmark Runner v1.0
=========================================
Bu betik WSL/Ubuntu üzerinde çalışır. Sırasıyla belirlenen modelleri yükler,
llama-server'ı başlatır, Iron Inquisitor v5.2 testlerini koşar,
raporları analiz eder ve C:\Kuroshin\docs\BENCHMARK_REPORT.md olarak
karşılaştırmalı bir Markdown raporu oluşturur.

Kullanım:
  python3 run_benchmarks.py
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/mnt/c/Kuroshin")
VENV_PYTHON = "/root/kuroshin/venv/bin/python3"
SWITCH_MODEL_PY = BASE_DIR / "scripts" / "switch_model.py"
INQUISITOR_PY = BASE_DIR / "scripts" / "iron_inquisitor" / "inquisitor_v5.py"
REPORT_DIR = BASE_DIR / "scripts" / "iron_inquisitor" / "reports"
OUTPUT_REPORT_MD = BASE_DIR / "docs" / "BENCHMARK_REPORT.md"

# Test edilmek istenen model desenleri
TARGET_PATTERNS = {
    "mevcut": "huihui",
    "deepseek_r1": "deepseek",
    "qwen3_coder": "coder"
}

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🚀 [{ts}] {msg}")

def check_llama_healthy(url="http://127.0.0.1:8080/health", timeout=2, max_retries=15) -> bool:
    for i in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False

def get_latest_report(start_time: float) -> Path | None:
    if not REPORT_DIR.exists():
        return None
    reports = sorted(REPORT_DIR.glob("inquisitor_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return None
    # Test başladıktan sonra üretilmiş olan en güncel dosyayı al
    latest = reports[0]
    if latest.stat().st_mtime >= start_time:
        return latest
    return None

def run_model_test(model_name: str) -> dict | None:
    log(f"Model yükleniyor: {model_name}")
    
    # 1. Model Geçişi yap (switch_model.py)
    cmd_switch = [VENV_PYTHON, str(SWITCH_MODEL_PY), "switch", model_name, "--json"]
    res = subprocess.run(cmd_switch, capture_output=True, text=True)
    if res.returncode != 0:
        log(f"❌ Model geçişi başarısız: {res.stderr or res.stdout}")
        return None
    
    try:
        switch_data = json.loads(res.stdout)
        log(f"Model geçişi tamamlandı: {switch_data.get('mesaj', '')}")
    except json.JSONDecodeError:
        log(f"⚠️ Model geçişi JSON çıktısı okunamadı, devam ediliyor. Çıktı: {res.stdout}")

    # 2. llama-server'ın hazır olmasını bekle
    log("llama-server'ın hazır olması bekleniyor...")
    if not check_llama_healthy(max_retries=30):
        log("❌ llama-server belirlenen sürede hazır olamadı!")
        return None
    log("llama-server aktif ve sağlıklı.")

    # 3. Hız Testi (Hız tespiti için switch_model.py status oku)
    tok_s = 0.0
    try:
        cmd_status = [VENV_PYTHON, str(SWITCH_MODEL_PY), "status"]
        res_status = subprocess.run(cmd_status, capture_output=True, text=True)
        # Hız çıktısını parse et ("Su an hiz: X.Y tok/s")
        for line in res_status.stdout.splitlines():
            if "hiz:" in line.lower():
                parts = line.split()
                for p in parts:
                    try:
                        tok_s = float(p)
                        break
                    except ValueError:
                        pass
    except Exception as e:
        log(f"⚠️ Hız testi okuma hatası: {e}")

    # 4. Iron Inquisitor testlerini çalıştır
    log("Iron Inquisitor testleri başlatılıyor...")
    start_time = time.time()
    
    # --skip-llama: llama-server'ı tekrar başlatmaya kalkmasın
    # --no-telegram: telegram spam'ini önlesin
    cmd_test = [VENV_PYTHON, str(INQUISITOR_PY), "--skip-llama", "--no-telegram"]
    res_test = subprocess.run(cmd_test, capture_output=True, text=True)
    
    # Rapor dosyasını bul
    report_file = get_latest_report(start_time)
    if not report_file:
        log("❌ Iron Inquisitor rapor dosyası bulunamadı!")
        return None
    
    try:
        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        total = len(report_data)
        passes = sum(1 for r in report_data if r.get("status") == "PASS")
        fails = total - passes
        fail_pct = round(100 * fails / total, 1) if total else 0.0
        
        # Testlerin ortalama süresi
        elapsed_list = [r.get("elapsed", 0) for r in report_data if "elapsed" in r]
        avg_elapsed = round(sum(elapsed_list) / len(elapsed_list), 2) if elapsed_list else 0.0
        
        # ASR (Attack Success Rate) hesabı
        attack_results = [r for r in report_data if r.get("expect_blocked", False)]
        total_attacks = len(attack_results)
        passed_through = sum(1 for r in attack_results if r.get("status") != "PASS")
        asr = round(passed_through / total_attacks, 3) if total_attacks else 0.0
        
        log(f"✅ Rapor analiz edildi. Toplam: {total} | Başarılı: {passes} | Hata: {fails} (%{fail_pct}) | Hız: {tok_s} tok/s")
        return {
            "model_name": model_name,
            "tok_s": tok_s,
            "total_tests": total,
            "passes": passes,
            "fails": fails,
            "fail_pct": fail_pct,
            "avg_elapsed_s": avg_elapsed,
            "asr": asr,
            "total_attacks": total_attacks,
            "blocked_attacks": total_attacks - passed_through,
            "report_path": str(report_file.name)
        }
    except Exception as e:
        log(f"❌ Rapor çözümleme hatası: {e}")
        return None

def main():
    if not SWITCH_MODEL_PY.exists():
        log(f"❌ switch_model.py bulunamadı: {SWITCH_MODEL_PY}")
        sys.exit(1)
    if not INQUISITOR_PY.exists():
        log(f"❌ inquisitor_v5.py bulunamadı: {INQUISITOR_PY}")
        sys.exit(1)

    log("Mevcut modeller taranıyor...")
    cmd_options = [VENV_PYTHON, str(SWITCH_MODEL_PY), "options", "--json"]
    res_options = subprocess.run(cmd_options, capture_output=True, text=True)
    if res_options.returncode != 0:
        log(f"❌ Modeller listelenemedi: {res_options.stderr}")
        sys.exit(1)
        
    try:
        options_data = json.loads(res_options.stdout)
        options = options_data.get("options", [])
    except Exception as e:
        log(f"❌ Model JSON parse hatası: {e}. Ham çıktı: {res_options.stdout}")
        sys.exit(1)

    # Adayları belirle
    candidates = {}
    for key, pattern in TARGET_PATTERNS.items():
        found = None
        for opt in options:
            model_val = opt.get("value", "")
            # Desen eşleşmesi kontrol et (örn. 'huihui' ismin içindeyse veya alias'ındaysa)
            if pattern in model_val.lower() or any(pattern in a.lower() for a in opt.get("aliases", [])):
                found = model_val
                break
        if found:
            candidates[key] = found
            log(f"Aday tespit edildi [{key}]: {found}")
        else:
            log(f"⚠️ Aday bulunamadı [{key}] (Desen: {pattern}). Modeli indirdiğinizden emin olun.")

    if not candidates:
        log("❌ Hiçbir benchmark adayı model bulunamadı! İşlem iptal ediliyor.")
        sys.exit(1)

    results = {}
    for key, model_name in candidates.items():
        log(f"\n=======================================================")
        log(f"BENCHMARK BAŞLIYOR: [{key.upper()}] - {model_name}")
        log(f"=======================================================")
        
        # Testi koş
        res = run_model_test(model_name)
        if res:
            results[key] = res
        else:
            log(f"❌ {model_name} için testler tamamlanamadı!")

    # Karşılaştırma Raporu Oluştur (docs/BENCHMARK_REPORT.md)
    log("Tüm testler bitti. Markdown raporu oluşturuluyor...")
    
    md_content = []
    md_content.append("# 📊 KUROSHİN OTOMATİK MODEL KARŞILAŞTIRMA RAPORU")
    md_content.append(f"**Oluşturulma Tarihi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_content.append("Bu rapor, yerel donanımda çalışan modellerin otonom olarak test edilmesiyle otomatik üretilmiştir.\n")
    
    md_content.append("## 📈 1. Genel Performans Karşılaştırma Tablosu\n")
    md_content.append("| Model Rolü | Model Dosya Adı | Başarı Oranı | Hata Oranı | Hız (tok/s) | Ort. Test Süresi | Güvenlik (ASR) | Rapor Dosyası |")
    md_content.append("|---|---|---|---|---|---|---|---|")
    
    for key, res in results.items():
        success_pct = f"%{100 - res['fail_pct']:.1f}"
        fail_pct = f"%{res['fail_pct']:.1f}"
        asr_pct = f"%{res['asr'] * 100:.1f}"
        role = {
            "mevcut": "Mevcut (Qwen3.6-35B)",
            "deepseek_r1": "DeepSeek R1 (32B)",
            "qwen3_coder": "Qwen3 Coder (30B)"
        }.get(key, key.upper())
        
        md_content.append(
            f"| **{role}** | `{res['model_name']}` | **{success_pct}** | {fail_pct} | {res['tok_s']} | {res['avg_elapsed_s']}s | {asr_pct} ({res['blocked_attacks']}/{res['total_attacks']}) | [{res['report_path']}](file:///C:/Kuroshin/scripts/iron_inquisitor/reports/{res['report_path']}) |"
        )
        
    md_content.append("\n## 🎯 2. Karar ve Değerlendirme Analizi\n")
    
    # Basit bir karar algoritması raporu
    if len(results) >= 2:
        best_coder = results.get("qwen3_coder")
        best_r1 = results.get("deepseek_r1")
        current = results.get("mevcut")
        
        md_content.append("### 💡 Donanım ve Hız Değerlendirmesi:")
        if best_coder and current:
            speed_gain = round(best_coder["tok_s"] - current["tok_s"], 1)
            if speed_gain > 0:
                md_content.append(f"* **Qwen3 Coder**, mevcut modele göre **+{speed_gain} tok/s** daha hızlı çıktı üretiyor. MoE mimarisi sayesinde hız avantajı yerel cihazda oldukça belirgin.")
            else:
                md_content.append("* Qwen3 Coder ve Mevcut Model benzer hız eğrilerine sahip.")
                
        if best_r1:
            md_content.append(f"* **DeepSeek R1 (32B)**, derin düşünme `<think>` token'ları ürettiği için kelime hızında daha yavaş bir grafik çizdi (Ort. gecikme: {best_r1['avg_elapsed_s']}s).")

        md_content.append("\n### 🛠️ Ajan Entegrasyonu ve Kararlılık:")
        if best_coder and best_r1:
            if best_coder["fail_pct"] < best_r1["fail_pct"]:
                md_content.append(f"* **Qwen3 Coder (%{100 - best_coder['fail_pct']:.1f} Başarı)**, DeepSeek R1'e göre araç çağırma (tool-calling) testlerinde daha kararlı duruş sergiledi. Kodlama ve ajan entegrasyonu için daha güvenli bir liman.")
            elif best_coder["fail_pct"] > best_r1["fail_pct"]:
                md_content.append(f"* **DeepSeek R1 (%{100 - best_r1['fail_pct']:.1f} Başarı)**, otonom problem çözme ve mantık gerektiren test suitlerinde daha yüksek başarı gösterdi.")
            else:
                md_content.append("* Her iki yeni model de benzer test başarı oranlarına sahip.")
    else:
        md_content.append("Karşılaştırma raporu oluşturabilmek için en az 2 modelin başarıyla test edilmesi gerekmektedir.\n")

    md_content.append("\n## 🚀 3. Nihai Tavsiye (Tavsiye Edilen Karar)\n")
    if results:
        # En düşük hata oranına sahip olanı seç
        best_key = min(results, key=lambda k: results[k]["fail_pct"])
        best_model = results[best_key]
        role_name = {
            "mevcut": "Mevcut Model",
            "deepseek_r1": "DeepSeek R1 (32B)",
            "qwen3_coder": "Qwen3 Coder (30B)"
        }.get(best_key, best_key)
        
        md_content.append(f"Yapılan otonom test sonuçlarına göre Kuroshin OS için en başarılı aday: **{role_name}** (`{best_model['model_name']}`).")
        md_content.append(f"Bu model test suitini **%{100 - best_model['fail_pct']:.1f} başarı oranı** ile tamamlayarak en stabil performansı göstermiştir.")
    
    OUTPUT_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT_MD.write_text("\n".join(md_content), encoding="utf-8")
    
    log(f"Karşılaştırma Raporu başarıyla oluşturuldu: {OUTPUT_REPORT_MD}")
    log("İşlem tamamlandı.")

if __name__ == "__main__":
    main()
