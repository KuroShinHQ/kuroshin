"""Iron Inquisitor v6 — Merkezi Yapilandirma (v5 geriye donuk uyumlu)

v5.py eski yollar kullaniyordu (/mnt/c/Kuroshin, /root/kuroshin/venv).
Bu modul guncel KuroshinHQ yollarini tek noktadan saglar.
"""
from pathlib import Path

# ── Kok dizinler (guncel) ─────────────────────────────────────────────
BASE        = Path("/mnt/c/KuroshinHQ")
WSL_VENV    = "/opt/kuroshin/venv/bin/python3"
WIN_VENV    = str(BASE / "_hub" / "venv" / "Scripts" / "python.exe")

# ── Servisler ─────────────────────────────────────────────────────────
LLAMA_URL   = "http://127.0.0.1:8080/v1/chat/completions"
LLAMA_HEALTH = "http://127.0.0.1:8080/health"
BRIDGE_URL  = "http://127.0.0.1:3005"
CHROMA_URL  = "http://127.0.0.1:8100"
TOR_SOCKS   = "127.0.0.1:9050"

# ── MCP sunucu komutlari (v5 MCP_SERVERS ile uyumlu isimler) ─────────
MCP_SERVERS = {
    "kuroshin-echo":     [WSL_VENV, str(BASE / "mcp_servers/echo_server/kuroshin_echo.py")],
    "kuroshin-search":   [WSL_VENV, str(BASE / "mcp_servers/search_server/kuroshin_search_mcp.py")],
    "kuroshin-bridge":   [WSL_VENV, str(BASE / "mcp_servers/bridge_server/kuroshin_bridge_mcp.py")],
    "kuroshin-walker":   [WSL_VENV, str(BASE / "mcp_servers/walker_server/kuroshin_walker_mcp.py")],
    "kuroshin-council":  [WSL_VENV, str(BASE / "mcp_servers/council_server/kuroshin_council_mcp.py")],
    "kuroshin-deerflow": [WSL_VENV, str(BASE / "mcp_servers/deerflow_server/kuroshin_deerflow_mcp.py")],
    "kuroshin-playwright":[WSL_VENV, str(BASE / "mcp_servers/playwright_server/server.py")],
    "kuroshin-memory":   ["/opt/kuroshin/venv/bin/chroma-mcp", "--client-type", "persistent",
                          "--data-dir", "/root/kuroshin/memory/chroma"],
}

# ── Log / rapor / arsiv yollari ──────────────────────────────────────
HERE_DIR    = Path(__file__).resolve().parent          # iron_inquisitor/
SUITES_DIR  = HERE_DIR.parent / "suites"               # JSON suite'ler (tasima gerekirse)
SUITES_DIR_LEGACY = HERE_DIR.parent                    # v5: suite'ler iron_inquisitor/ icinde
REPORTS_DIR = HERE_DIR.parent / "reports"
MODELS_DIR  = HERE_DIR.parent / "models"               # arena model arsivi
MCPS_DIR    = HERE_DIR.parent / "mcps"                 # MCP kapasite sonuclari
TESTS_DIR   = HERE_DIR.parent / "tests"                # v6 unit testleri
LOGS_DIR    = HERE_DIR.parent / "logs"                 # v6 JSONL loglar

# ── Dokumanlar (otomatik MD rapor hedefleri) ────────────────────────
DOCS_HUB       = BASE / "_hub" / "docs"
MODEL_KARSILASTIRMA_MD = DOCS_HUB / "MODEL_KARSILASTIRMA_20260819.md"
MODEL_TEST_PLANI_MD    = BASE / "kuroshin" / "docs" / "MODEL_TEST_PLANI.md"

# ── Cagri varsayilanlari ─────────────────────────────────────────────
DEFAULT_MODEL  = "kuroshin"
DEFAULT_TEMP   = 0.3
DEFAULT_MAX_TOK = 2048

# ── Calisma modu tespiti: WSL mi Windows mu? ─────────────────────────
def is_wsl() -> bool:
    try:
        return Path("/proc/version").exists()
    except Exception:
        return False

def python() -> str:
    return WSL_VENV if is_wsl() else WIN_VENV