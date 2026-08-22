"""Iron Inquisitor v6 — Runner: paralel + deadline butcesi + adaptive timeout + retry

Kanitlar (web):
  - multigrid.ai/learn/llm-timeouts: deadline butcesi (kalan sure = min(timeout, budget)),
    stall timeout (token arasi gap), retry deadlinedan once anlamli mi kontrolu
  - mergify.com/learn/auto-retry: sartli retry, max 1-2, retry orani metrik
  - v5'in ThreadPoolExecutor paralelizasyonu korunur (hafif x4 + agir x2)
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .timeouts import AdaptiveTimeout
from .retry import should_retry, retry_rate_warning


class DeadlineBudget:
    """Mutlak deadline: her adim min(kendi_timeout, kalan_butce) alir (multigrid)."""

    def __init__(self, total_seconds: float):
        self._deadline = time.monotonic() + total_seconds

    def remaining(self) -> float:
        left = self._deadline - time.monotonic()
        return max(0.0, left)

    def budget(self, preferred: float) -> float:
        left = self.remaining()
        if left <= 0:
            return 0.0
        return min(preferred, left)


def run_with_adaptive_timeout(run_fn, key: str, category: str = "",
                              attempt: int = 1, deadline: DeadlineBudget | None = None,
                              use_stall: bool = False) -> dict:
    """run_fn'yi adaptive timeout ile calistir.

    run_fn(timeout) -> dict  (status, note, output, elapsed...)
    """
    at = AdaptiveTimeout()
    base = at.get(key, category, attempt)
    if deadline is not None:
        base = deadline.budget(base)
        if base <= 0:
            return {"status": "DEADLINE", "note": "kalan butce yok", "output": "",
                    "elapsed": 0.0, "id": key, "tool": "", "category": category,
                    "score": 0.0, "weight": 1.0}

    result = run_fn(timeout=base)
    if result.get("elapsed") is None:
        result["elapsed"] = 0.0

    # Yalnizca basarili sureler EWMA'ya gider (timeout sansurlemesin)
    if result.get("status") == "PASS":
        at.record(key, result["elapsed"])
    at.save()
    return result


def run_with_retry(run_fn, key: str, category: str = "", max_retries: int = 1,
                   deadline: DeadlineBudget | None = None) -> dict:
    """Sartli retry: sadece TIMEOUT/ERROR + transient sinyal (mergify kurali)."""
    attempt = 1
    result = run_with_adaptive_timeout(run_fn, key, category, attempt=attempt,
                                       deadline=deadline)
    while attempt <= max_retries and should_retry(result):
        # multigrid: deadline'dan once retry deger mi?
        if deadline is not None and deadline.remaining() < 5:
            break
        attempt += 1
        print(f"    ↻ {key} retry #{attempt-1} (onceki: {result.get('status')})")
        result = run_with_adaptive_timeout(run_fn, key, category, attempt=attempt,
                                           deadline=deadline)
        if result.get("status") == "PASS":
            result["retried"] = True
    return result


def run_parallel(tests: list, run_fn, deadline_seconds: float = 1800,
                 light_workers: int = 4, heavy_workers: int = 2,
                 heavy_cats: set | None = None) -> list:
    """v5 paralelizasyonu + global deadline. run_fn(test) -> result dict."""
    heavy_cats = heavy_cats or {"web_fetch", "council"}
    deadline = DeadlineBudget(deadline_seconds)
    results = []
    lock = threading.Lock()

    def wrapped(t):
        return run_fn(t, deadline=deadline)

    light = [t for t in tests if t.get("category", "") not in heavy_cats]
    heavy = [t for t in tests if t.get("category", "") in heavy_cats]
    print(f"[V6] {len(light)} hafif (x{light_workers}) + {len(heavy)} agir (x{heavy_workers}), "
          f"deadline {deadline_seconds}s")

    with ThreadPoolExecutor(max_workers=light_workers) as ex:
        for f in as_completed({ex.submit(wrapped, t): t for t in light}):
            with lock:
                results.append(f.result())
    with ThreadPoolExecutor(max_workers=heavy_workers) as ex:
        for f in as_completed({ex.submit(wrapped, t): t for t in heavy}):
            with lock:
                results.append(f.result())

    warn = retry_rate_warning()
    if warn:
        print(f"[V6] {warn}")
    return results