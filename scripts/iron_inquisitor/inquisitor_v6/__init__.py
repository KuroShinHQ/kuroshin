"""Iron Inquisitor v6 — paket ana modulu.

v5.py monoliti BOZULMADAN yanina eklenir (geriye donuk uyumlu).
Kullanim:
    import sys; sys.path.insert(0, 'iron_inquisitor')
    from inquisitor_v6 import timeouts, retry, arena, runner
"""
from . import config
from .timeouts import AdaptiveTimeout
from .retry import FlakyTracker, should_retry, retry_rate, retry_rate_warning
from .arena import run_arena

__all__ = ["config", "AdaptiveTimeout", "FlakyTracker", "should_retry",
           "retry_rate", "retry_rate_warning", "run_arena"]

__version__ = "6.0.0"