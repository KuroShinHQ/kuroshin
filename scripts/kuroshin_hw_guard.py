#!/usr/bin/env python3
"""
Kuroshin Hardware Guard v1.0 (DALGA 5.6)
=========================================
Read-only API: agir is yapmadan once donanim durumunu kontrol et.

vram_guardian.py (daemon, 30s polling, SIGSTOP/SIGCONT) ile birlikte calisir
ama AYRI bir modul — vram_guardian'a dokunmaz, sadece NVML sorgular.

Esikler vram_guardian ile ayni:
  VRAM warn:    7500 MB    (LitServe+LiteLLM suspend tetigi)
  VRAM crit:    7800 MB    (ChromaDB de suspend tetigi)
  Temp warn:    85 °C      (uyari)
  Temp crit:    90 °C      (throttle riski)

Kullanim (chancellor full_power_query pre-check):
    from kuroshin_hw_guard import safe_for_heavy
    ok, reason = safe_for_heavy()
    if not ok:
        return f"Donanim zorlaniyor: {reason}"
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

VRAM_TOTAL_MB = 8188
VRAM_WARN_MB = 7500
VRAM_CRIT_MB = 7800
TEMP_WARN_C = 85
TEMP_CRIT_C = 90

THROTTLE_EVENT_LOG = Path("/root/kuroshin/logs/hw_throttle_events.jsonl")
THROTTLE_EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)


_NVML_HANDLE = None
_NVML_OK = False


def _init_nvml():
    global _NVML_HANDLE, _NVML_OK
    if _NVML_OK:
        return
    try:
        import pynvml
        pynvml.nvmlInit()
        _NVML_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
        _NVML_OK = True
    except Exception:
        _NVML_OK = False


def get_hw_status() -> Dict[str, Any]:
    """Anlik donanim metrigi (NVML)."""
    _init_nvml()
    if not _NVML_OK:
        return {
            "available": False,
            "vram_used_mb": 0,
            "vram_total_mb": VRAM_TOTAL_MB,
            "vram_pct": 0.0,
            "temp_c": 0,
            "throttle_active": False,
        }
    import pynvml
    try:
        info = pynvml.nvmlDeviceGetMemoryInfo(_NVML_HANDLE)
        used_mb = info.used // 1024 // 1024
        temp = pynvml.nvmlDeviceGetTemperature(_NVML_HANDLE, pynvml.NVML_TEMPERATURE_GPU)
        # Throttle reasons (NVML clock throttle)
        throttle_active = False
        try:
            reasons = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(_NVML_HANDLE)
            HW_THERMAL = getattr(pynvml, "nvmlClocksThrottleReasonHwThermalSlowdown", 0x40)
            SW_THERMAL = getattr(pynvml, "nvmlClocksThrottleReasonSwThermalSlowdown", 0x20)
            throttle_active = bool(reasons & (HW_THERMAL | SW_THERMAL))
        except Exception:
            pass
        return {
            "available": True,
            "vram_used_mb": int(used_mb),
            "vram_total_mb": VRAM_TOTAL_MB,
            "vram_pct": round(used_mb / VRAM_TOTAL_MB * 100, 1),
            "temp_c": int(temp),
            "throttle_active": throttle_active,
        }
    except Exception:
        return {
            "available": False,
            "vram_used_mb": 0,
            "vram_total_mb": VRAM_TOTAL_MB,
            "vram_pct": 0.0,
            "temp_c": 0,
            "throttle_active": False,
        }


def safe_for_heavy(reserve_mb: int = 500) -> Tuple[bool, str]:
    """Agir bir LLM cagrisi guvenli mi?

    Esik:
      - VRAM kullanim < VRAM_WARN_MB - reserve (yeni alloc icin yer var mi)
      - Temp < TEMP_WARN_C
      - Throttle aktif degil
    """
    s = get_hw_status()
    if not s["available"]:
        return True, "NVML yok — koruma atlandi"
    if s["vram_used_mb"] >= (VRAM_WARN_MB - reserve_mb):
        return False, (
            f"VRAM dolu: {s['vram_used_mb']}/{VRAM_TOTAL_MB} MB "
            f"(>{VRAM_WARN_MB - reserve_mb} esigi)"
        )
    if s["temp_c"] >= TEMP_WARN_C:
        return False, f"GPU sicakligi yuksek: {s['temp_c']}°C (>{TEMP_WARN_C} esigi)"
    if s["throttle_active"]:
        return False, "GPU thermal throttle aktif"
    return True, "ok"


def short_status_line() -> str:
    s = get_hw_status()
    if not s["available"]:
        return "🔘 HW: NVML yok"
    v_em = "🟢" if s["vram_used_mb"] < VRAM_WARN_MB else ("🟡" if s["vram_used_mb"] < VRAM_CRIT_MB else "🔴")
    t_em = "🟢" if s["temp_c"] < TEMP_WARN_C else ("🟡" if s["temp_c"] < TEMP_CRIT_C else "🔴")
    th = " 🔥THROTTLE" if s["throttle_active"] else ""
    return f"{v_em} VRAM {s['vram_used_mb']}/{VRAM_TOTAL_MB}MB ({s['vram_pct']}%) | {t_em} {s['temp_c']}°C{th}"


def record_throttle_event(context: str = "", extra: Optional[Dict[str, Any]] = None) -> None:
    s = get_hw_status()
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "context": context,
        "status": s,
    }
    if extra:
        entry["extra"] = extra
    with THROTTLE_EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _self_test():
    print("[kuroshin_hw_guard] self_test")
    s = get_hw_status()
    print(json.dumps(s, indent=2, ensure_ascii=False))
    ok, reason = safe_for_heavy()
    print(f"safe_for_heavy: {ok} — {reason}")
    print(f"status_line: {short_status_line()}")
    record_throttle_event("self_test")
    print(f"event log: {THROTTLE_EVENT_LOG}")


if __name__ == "__main__":
    _self_test()
