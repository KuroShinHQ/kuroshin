"""kuroshin birim test ortami — servis/ag gerektirmez.

KUROSHIN_HOME gecici dizine yonlendirilir; chancellor import'u log dosyalarini
oraya yazar (gercek memory/logs'a dokunmaz).
"""
import os
import sys
import tempfile
from pathlib import Path

# Import'tan ONCE env ayarlanmali — chancellor KUROSHIN_ROOT'i import aninda hesaplar.
_TEST_ROOT = Path(tempfile.gettempdir()) / "kuroshin_unit_test_root"
(_TEST_ROOT / "logs").mkdir(parents=True, exist_ok=True)
(_TEST_ROOT / "memory").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("KUROSHIN_HOME", str(_TEST_ROOT))

_REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO / "tests" / "unit"))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def chancellor():
    """chancellor modulu (tek import — agir bagimliliklar bir kez Yuklenir)."""
    import agents.kuroshin_chancellor as ch

    return ch


@pytest.fixture(scope="session")
def security():
    from kuroshin_security import check_command, sanitize_web_content, scan_for_injection

    return type("Sec", (), {
        "check_command": staticmethod(check_command),
        "scan_for_injection": staticmethod(scan_for_injection),
        "sanitize_web_content": staticmethod(sanitize_web_content),
    })
