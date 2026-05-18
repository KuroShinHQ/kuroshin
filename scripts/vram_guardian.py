#!/usr/bin/env python3
"""
Kuroshin VRAM Muhafızı v1.1
Her 30 saniyede VRAM ve GPU sıcaklık kontrol eder.
Eşikler: 7500MB → LitServe+LiteLLM suspend | 7800MB → ChromaDB suspend
Sıcaklık: 85°C → uyarı log | 90°C → kritik log (throttling riski)
"""
import subprocess
import time
import sys
from pathlib import Path

try:
    import pynvml
    pynvml.nvmlInit()
    GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
    NVML_OK = True
except Exception as e:
    print(f"[WARN] NVML başlatılamadı: {e}", flush=True)
    NVML_OK = False

THRESHOLD_SUSPEND = 7500   # MB — LitServe + LiteLLM suspend
THRESHOLD_CRITICAL = 7800  # MB — ChromaDB de suspend
TEMP_WARN = 85             # °C — uyarı
TEMP_CRITICAL = 90         # °C — throttling riski
CHECK_INTERVAL = 30        # saniye

LOG_FILE = Path("/root/kuroshin/logs/vram_guardian.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

_suspended_litserve = False
_suspended_litellm = False
_suspended_chroma = False


def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_vram_mb() -> int:
    if not NVML_OK:
        return 0
    try:
        info = pynvml.nvmlDeviceGetMemoryInfo(GPU_HANDLE)
        return info.used // 1024 // 1024
    except Exception:
        return 0


def get_temp_c() -> int:
    if not NVML_OK:
        return 0
    try:
        return pynvml.nvmlDeviceGetTemperature(GPU_HANDLE, pynvml.NVML_TEMPERATURE_GPU)
    except Exception:
        return 0


def is_running(pattern: str) -> bool:
    result = subprocess.run(["pgrep", "-f", pattern], capture_output=True)
    return result.returncode == 0


def suspend_service(pattern: str, name: str):
    result = subprocess.run(["pkill", "-STOP", "-f", pattern], capture_output=True)
    if result.returncode == 0:
        log(f"[SUSPEND] {name} durduruldu (SIGSTOP)")
    else:
        log(f"[WARN] {name} durdurulamadı (zaten kapalı?)")


def resume_service(pattern: str, name: str):
    result = subprocess.run(["pkill", "-CONT", "-f", pattern], capture_output=True)
    if result.returncode == 0:
        log(f"[RESUME] {name} devam ettirildi (SIGCONT)")


def check_and_act():
    global _suspended_litserve, _suspended_litellm, _suspended_chroma

    vram = get_vram_mb()
    total = 8188

    # Kritik eşik — ChromaDB de suspend
    if vram >= THRESHOLD_CRITICAL:
        log(f"[KRİTİK] VRAM {vram}MB/{total}MB — ChromaDB suspend ediliyor!")
        if not _suspended_litserve:
            suspend_service("kuroshin_litserve", "LitServe")
            _suspended_litserve = True
        if not _suspended_litellm:
            suspend_service("litellm.proxy.proxy_server", "LiteLLM")
            _suspended_litellm = True
        if not _suspended_chroma:
            suspend_service("chroma run", "ChromaDB")
            _suspended_chroma = True

    # Uyarı eşiği — LitServe + LiteLLM suspend
    elif vram >= THRESHOLD_SUSPEND:
        log(f"[UYARI] VRAM {vram}MB/{total}MB — LitServe+LiteLLM suspend ediliyor")
        if not _suspended_litserve:
            suspend_service("kuroshin_litserve", "LitServe")
            _suspended_litserve = True
        if not _suspended_litellm:
            suspend_service("litellm.proxy.proxy_server", "LiteLLM")
            _suspended_litellm = True
        # ChromaDB resume (kritikten döndüyse)
        if _suspended_chroma:
            resume_service("chroma run", "ChromaDB")
            _suspended_chroma = False

    # Normal — resume
    else:
        if _suspended_litserve:
            resume_service("kuroshin_litserve", "LitServe")
            _suspended_litserve = False
        if _suspended_litellm:
            resume_service("litellm.proxy.proxy_server", "LiteLLM")
            _suspended_litellm = False
        if _suspended_chroma:
            resume_service("chroma run", "ChromaDB")
            _suspended_chroma = False

    return vram


def main():
    log(f"VRAM Muhafızı v1.1 başlatıldı — VRAM eşik: {THRESHOLD_SUSPEND}/{THRESHOLD_CRITICAL}MB, Sıcaklık: {TEMP_WARN}/{TEMP_CRITICAL}°C, interval: {CHECK_INTERVAL}s")

    while True:
        try:
            vram = check_and_act()
            temp = get_temp_c()
            pct = round(vram / 8188 * 100, 1)
            vram_status = "🟢" if vram < THRESHOLD_SUSPEND else ("🟡" if vram < THRESHOLD_CRITICAL else "🔴")
            temp_status = "🟢" if temp < TEMP_WARN else ("🟡" if temp < TEMP_CRITICAL else "🔴")

            if temp >= TEMP_CRITICAL:
                log(f"[KRİTİK SICAKLIK] {temp}°C — Thermal throttling riski! Inference yavaşlayabilir.")
            elif temp >= TEMP_WARN:
                log(f"[SICAKLIK UYARI] {temp}°C — Üst limite yaklaşıyor.")

            log(f"{vram_status} VRAM: {vram}MB/8188MB ({pct}%) | {temp_status} Sıcaklık: {temp}°C")
        except Exception as e:
            log(f"[HATA] {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
