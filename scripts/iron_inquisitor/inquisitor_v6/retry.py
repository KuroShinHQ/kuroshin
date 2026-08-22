"""Iron Inquisitor v6 — Sartli Retry + Flaky Tespiti

Kaynaklar (web, kanitli):
  - mergify.com/learn/auto-retry: retry YALNIZCA bilinen transient sinyallerde
    (timeout, network, exit code); max 1-2 deneme; retry_orani METRIK olarak izlenir
    (%30'u asarsa suite bozuktur, retry gizliyor demektir).
  - getpanto.ai/blog/detect-flaky-tests: flaky = fail->pass gecis orani >%75,
    runtime varyansi (z-score), timeout sinirina yakinlik.
"""
import json
import math
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
MAX_RETRIES = 1                      # mergify: 1-2 pratik tavan
RETRY_RATE_ALERT = 0.30              # retry orani %30'u asarsa flaky uyari

# Transient sinyal seti — sadece bunlar retry edilir
TRANSIENT_MARKERS = [
    "TIMEOUT", "timed out", "Connection refused", "Connection reset",
    "connection refused", "network", "getaddrinfo", "temporary",
    "ECONN", "ETIMEDOUT", "Broken pipe", "Server disconnected",
]


def is_transient(result_note: str, status: str = "") -> bool:
    """Retry edilebilir mi? (mergify: yalnizca bilinen transient sinyaller)"""
    if status == "TIMEOUT":
        return True
    low = (result_note or "").lower()
    return any(m.lower() in low for m in TRANSIENT_MARKERS)


def should_retry(result: dict) -> bool:
    """Sartli retry karari — gercek basarisizliklar (FAIL) retry EDILMEZ."""
    return result.get("status") in ("TIMEOUT", "ERROR") and is_transient(
        result.get("note", "") + result.get("output", ""), result.get("status", ""))


class FlakyTracker:
    """Son raporlardan flaky tespiti: z-score + fail->pass orani.

    Kanit (panto): fail->pass gecis orani >%75 flaky; z-score yuksek varyans uyarir.
    """

    def __init__(self, report_dir: Path = REPORT_DIR):
        self.report_dir = report_dir

    def _load_reports(self, limit: int = 10) -> list[dict]:
        if not self.report_dir.exists():
            return []
        files = sorted(self.report_dir.glob("inquisitor_*.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
        out = []
        for f in files:
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
        return out

    def analyze(self, test_id: str) -> dict:
        """test_id icin flaky analiz: {status, reason, z_score, fail_pass_ratio}"""
        reports = self._load_reports()
        if not reports:
            return {"status": "NO_DATA", "reason": "yeterli rapor yok"}

        outcomes: list[str] = []
        durations: list[float] = []
        for rep in reports:
            for r in rep:
                if r.get("id") == test_id:
                    outcomes.append(r.get("status", "?"))
                    if r.get("elapsed"):
                        durations.append(float(r["elapsed"]))

        if not outcomes:
            return {"status": "NO_DATA", "reason": "test raporlarda yok"}

        # fail->pass orani (panto): onceki FAIL + sonraki PASS
        transitions = [(outcomes[i], outcomes[i + 1]) for i in range(len(outcomes) - 1)]
        fail_pass = [t for t in transitions if t[0] in ("FAIL", "TIMEOUT") and t[1] == "PASS"]
        fail_pass_ratio = len(fail_pass) / max(len(transitions), 1)

        # z-score: sure varyansi (sadece >2 ornek)
        z = None
        if len(durations) >= 3:
            mean = sum(durations) / len(durations)
            var = sum((d - mean) ** 2 for d in durations) / len(durations)
            std = math.sqrt(var) if var else 0.0
            if std > 0 and durations:
                z = (max(durations) - mean) / std

        flaky = fail_pass_ratio > 0.75 or (z is not None and z > 3.0)
        return {
            "status": "FLAKY" if flaky else "STABLE",
            "reason": f"fail->pass orani={fail_pass_ratio:.2f}, z={z if z is not None else 'n/a'}",
            "fail_pass_ratio": fail_pass_ratio,
            "z_score": z,
            "outcome_history": outcomes[-10:],
        }


def retry_rate(reports_dir: Path = REPORT_DIR, limit: int = 10) -> float:
    """Son raporlardan retry ihtiyaci orani — metrik (mergify: izle, gizleme)."""
    # Basit proxy: TIMEOUT/ERROR orani. (Retry gercekte runner'da uygulanir.)
    if not reports_dir.exists():
        return 0.0
    files = sorted(reports_dir.glob("inquisitor_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    total = transient = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for r in data:
                total += 1
                if r.get("status") in ("TIMEOUT", "ERROR"):
                    transient += 1
        except Exception:
            pass
    return transient / max(total, 1)


def retry_rate_warning() -> str | None:
    rate = retry_rate()
    if rate > RETRY_RATE_ALERT:
        return (f"⚠️ Retry orani %{rate*100:.0f} esigi asti (%{RETRY_RATE_ALERT*100:.0f}). "
                f"Suite bozuk olabilir — retry sorunu gizliyor. (mergify kurali)")
    return None