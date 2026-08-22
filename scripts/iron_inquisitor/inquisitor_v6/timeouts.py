"""Iron Inquisitor v6 — Adaptive Timeout (EWMA + stall)

Kaynaklar (web, kanitli):
  - holepunchto/adaptive-timeout + ahmedsoliman/adaptive-timeout (FB LogDevice EWMA)
    timeout = (avg + 2*variance) * attempt, fallback sabit dizi
  - multigrid.ai/learn/llm-timeouts: ilk-chunk (TTFT) ve stall (inter-token gap) AYRI;
    genel: timeout = quantile(basarili_sureler, q) * safety
  - Yalnizca BASARILI sureler kaydedilir (timeout olanlar dagilimi sansurler -> EWMA kuculur)
"""
import json
import time
from collections import defaultdict
from pathlib import Path

HISTORY_FILE = Path(__file__).resolve().parent.parent / "reports" / "timeout_history.json"

# Varsayilan fallback: test kategorisine gore baslangic timeout (v5 fix_timeouts map'i)
FALLBACK_TIMEOUTS = {
    "tool_use": 60, "web_search": 90, "web_fetch": 90, "file_ops": 60,
    "service_check": 45, "council": 120, "path_correctness": 60,
    "hallucination_guard": 60, "chroma_fix": 60, "model_mgmt": 60,
    "bat_menu": 60, "proactive": 60, "pdf_fetch": 90, "memory": 60,
    "tool_verify": 60, "model_red": 90, "model_reasoning": 120,
    "model_codegen": 90, "model_json": 60, "model_context": 120,
    "security_v5": 30, "security_v4": 30, "think_chain": 90,
    "autonomous_agent": 90, "doom_pipeline": 60, "circuit_breaker": 30,
}

# llm-timeouts kurali: quantile * safety
QUANTILE = 0.99          # kullanim yolu icin p99
SAFETY   = 1.5           # drifte karsi (1.5-2.0 onerilir)
MIN_TIMEOUT  = 10.0      # floor
MAX_TIMEOUT  = 600.0     # tavan (v5 max 360 model testleri; 600 guvenli)
STALL_DEFAULT = 9.0      # token arasi gap limiti (multigrid: gap * 5 onerisi)
TTFT_DEFAULT  = 5.0      # ilk chunk bekleme (kucuk promptlar icin)

# EWMA parametreleri (TCP usulu)
EWMA_AVG_WEIGHT  = 0.875   # yeni ornek 0.125 agirlik
EWMA_VAR_WEIGHT  = 0.75


class AdaptiveTimeout:
    """Test ID/kategori bazli EWMA adaptive timeout + stall kurali.

    Kullanim:
        at = AdaptiveTimeout()
        timeout = at.get("model-red-01", category="model_red", attempt=1)
        ... test calistir ...
        at.record("model-red-01", elapsed=95.2)   # YALNIZCA basarili olanlar
        at.save()
    """

    def __init__(self, history_path: Path = HISTORY_FILE):
        self.history_path = history_path
        self._samples: dict[str, list[float]] = defaultdict(list)
        self._load()

    # ── kalicilik ─────────────────────────────────────────────────────
    def _load(self):
        try:
            if self.history_path.exists():
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._samples[k] = list(v)
        except Exception:
            pass

    def save(self):
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            # En fazla son 50 ornek tut (hafiza + eski veri gecersiz)
            trimmed = {k: v[-50:] for k, v in self._samples.items()}
            self.history_path.write_text(
                json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ── kayit ─────────────────────────────────────────────────────────
    def record(self, key: str, elapsed: float):
        if elapsed <= 0:
            return
        self._samples[key].append(float(elapsed))

    # ── hesap ─────────────────────────────────────────────────────────
    def _ewma(self, values: list[float]) -> tuple[float, float]:
        avg = values[0]
        var = 0.0
        for v in values[1:]:
            diff = v - avg
            avg = avg * EWMA_AVG_WEIGHT + v * (1 - EWMA_AVG_WEIGHT)
            var = var * EWMA_VAR_WEIGHT + abs(diff) * (1 - EWMA_VAR_WEIGHT)
        return avg, var

    def get(self, key: str, category: str = "", attempt: int = 1) -> float:
        values = self._samples.get(key, [])
        # Ilk cagri: kayit yoksa kategori fallback'ine, o da yoksa 90s
        if not values:
            base = FALLBACK_TIMEOUTS.get(category, 90)
        else:
            # quantile tabanli (multigrid): p99 * safety, EWMA ile kombinasyon
            sorted_v = sorted(values)
            idx = min(len(sorted_v) - 1, int(len(sorted_v) * QUANTILE))
            quant = sorted_v[idx]
            avg, var = self._ewma(values)
            base = max(quant * SAFETY, avg + 2 * var)
        # Deneme sayisina gore linear backoff (LogDevice usulu)
        adaptive = base * attempt
        return round(max(MIN_TIMEOUT, min(adaptive, MAX_TIMEOUT)), 1)

    # ── stall / TTFT (multigrid kurali) ───────────────────────────────
    @staticmethod
    def stall_timeout() -> float:
        return STALL_DEFAULT

    @staticmethod
    def ttft_timeout() -> float:
        return TTFT_DEFAULT