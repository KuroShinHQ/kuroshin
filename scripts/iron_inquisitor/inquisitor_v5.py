#!/usr/bin/env python3
"""
Iron Inquisitor v5.2 — Self-Healing Test Motoru
Tek tuşla çalışır: gerekli servisleri otomatik başlatır, testleri yapar, rapor verir.
OpenClaude'a bağımlılık YOK. MCP sunucularını direkt stdio ile çağırır.
"""
import subprocess, json, sys, time, os, re, threading, select
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, urllib.error

sys.stdout.reconfigure(line_buffering=True)

BASE       = Path("/mnt/c/Kuroshin")
VENV_PY    = "/root/kuroshin/venv/bin/python3"
CHROMA_MCP = "/root/kuroshin/venv/bin/chroma-mcp"
LLAMA_URL  = "http://127.0.0.1:8080/v1/chat/completions"
BRIDGE_URL = "http://127.0.0.1:3005"
REPORT_DIR = Path(__file__).parent / "reports"

MCP_SERVERS = {
    "kuroshin-echo":    [VENV_PY, str(BASE / "mcp_servers/echo_server/kuroshin_echo.py")],
    "kuroshin-search":  [VENV_PY, str(BASE / "mcp_servers/search_server/kuroshin_search_mcp.py")],
    "kuroshin-bridge":  [VENV_PY, str(BASE / "mcp_servers/bridge_server/kuroshin_bridge_mcp.py")],
    "kuroshin-walker":  [VENV_PY, str(BASE / "mcp_servers/walker_server/kuroshin_walker_mcp.py")],
    "kuroshin-council": [VENV_PY, str(BASE / "mcp_servers/council_server/kuroshin_council_mcp.py")],
    "kuroshin-deerflow":[VENV_PY, str(BASE / "mcp_servers/deerflow_server/kuroshin_deerflow_mcp.py")],
    "kuroshin-memory":  [CHROMA_MCP, "--client-type", "persistent",
                         "--data-dir", "/root/kuroshin/memory/chroma"],
}

# ─────────────────────────────────────────────
# SERVİS YÖNETİMİ
# ─────────────────────────────────────────────

def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def wait_port(host: str, port: int, max_wait: int = 90, label: str = "") -> bool:
    for i in range(max_wait):
        if port_open(host, port):
            print(f"[INIT] {label} hazır ({i}s)")
            return True
        time.sleep(1)
    print(f"[INIT] ⚠️ {label} {max_wait}s içinde açılmadı")
    return False

def start_bridge() -> bool:
    """Agent Bridge (port 3005) — Windows node process, WSL içinden cmd.exe ile."""
    if port_open("127.0.0.1", 3005):
        print("[INIT] Agent Bridge ✅ (zaten çalışıyor)")
        return True
    print("[INIT] Agent Bridge başlatılıyor...")
    subprocess.Popen(
        ["/mnt/c/Windows/System32/cmd.exe", "/c",
         "set KUROSHIN_ROOT=C:\\Kuroshin&& node C:\\Kuroshin\\scripts\\agent_bridge.js"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return wait_port("127.0.0.1", 3005, max_wait=15, label="Agent Bridge (3005)")

def start_llama() -> bool:
    """Llama-server (port 8080) — nohup ile WSL içinde başlat."""
    if port_open("127.0.0.1", 8080):
        print("[INIT] llama-server ✅ (zaten çalışıyor)")
        return True
    print("[INIT] llama-server başlatılıyor (60-90s sürebilir)...")
    subprocess.Popen(
        ["/bin/bash", "/mnt/c/Kuroshin/scripts/start_llama.sh"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return wait_port("127.0.0.1", 8080, max_wait=90, label="llama-server (8080)")

def start_walker() -> bool:
    """Walker servisi (port 9002) — uvicorn, nohup ile başlat."""
    if port_open("127.0.0.1", 9002):
        print("[INIT] Walker ✅ (zaten çalışıyor)")
        return True
    print("[INIT] Walker başlatılıyor...")
    log = Path("/root/kuroshin/logs/walker.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as lf:
        subprocess.Popen(
            ["/bin/bash", "-c",
             "source /root/kuroshin/venv/bin/activate && cd /mnt/c/Kuroshin/agents && "
             "nohup python3 -u -m uvicorn kuroshin_walker_service:app "
             "--host 127.0.0.1 --port 9002 --loop asyncio --log-level warning &"],
            stdout=lf, stderr=lf
        )
    return wait_port("127.0.0.1", 9002, max_wait=20, label="Walker (9002)")

def ensure_services(skip_llama: bool = False):
    """Test başlamadan önce tüm servisleri hazır et."""
    print("[INIT] ── Servis Kontrolü ──────────────────────")
    bridge_ok = start_bridge()
    walker_ok = start_walker()
    llama_ok  = True
    if not skip_llama:
        llama_ok = start_llama()
    print(f"[INIT] Bridge:{bridge_ok} Walker:{walker_ok} Llama:{llama_ok}")
    print("[INIT] ─────────────────────────────────────────")
    return {"bridge": bridge_ok, "walker": walker_ok, "llama": llama_ok}

# ─────────────────────────────────────────────
# MCP STDIO İSTEMCİSİ
# ─────────────────────────────────────────────

def mcp_call(server_name: str, tool_name: str, args: dict, timeout: int = 60) -> str:
    cmd = MCP_SERVERS.get(server_name)
    if not cmd:
        return f"ERROR: unknown server {server_name}"
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            bufsize=1
        )

        def write_line(obj):
            proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
            proc.stdin.flush()

        def read_response(target_id, deadline):
            while time.time() < deadline:
                try:
                    proc.stdout.fileno()
                except Exception:
                    break
                ready, _, _ = select.select([proc.stdout], [], [], 0.5)
                if ready:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    line = line.strip()
                    if not line or not line.startswith("{"):
                        continue
                    try:
                        obj = json.loads(line)
                        if obj.get("id") == target_id:
                            return obj
                    except Exception:
                        continue
            return None

        deadline = time.time() + timeout

        write_line({"jsonrpc":"2.0","id":1,"method":"initialize",
            "params":{"protocolVersion":"2024-11-05","capabilities":{},
                      "clientInfo":{"name":"inquisitor","version":"5.1"}}})
        init_resp = read_response(1, min(deadline, time.time() + 10))
        if not init_resp:
            proc.kill()
            return "TIMEOUT: initialize"

        write_line({"jsonrpc":"2.0","method":"notifications/initialized"})
        write_line({"jsonrpc":"2.0","id":2,"method":"tools/call",
            "params":{"name":tool_name,"arguments":args}})

        tool_resp = read_response(2, deadline)
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

        if not tool_resp:
            return f"TIMEOUT: tool_call ({timeout}s)"
        if "error" in tool_resp:
            return f"MCP_ERROR: {tool_resp['error']}"

        content = tool_resp.get("result", {}).get("content", [])
        if isinstance(content, list):
            parts = [c.get("text","") for c in content if isinstance(c, dict) and c.get("text")]
            return "\n".join(parts)
        elif isinstance(content, str):
            return content
        return json.dumps(tool_resp.get("result", {}))

    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        return f"ERROR: {e}"

# ─────────────────────────────────────────────
# ARGÜMAN ÇIKARICI
# ─────────────────────────────────────────────

def extract_args(prompt: str, tool_name: str) -> dict:
    m_quoted = re.search(r"['\"]([A-Z0-9_]{3,50})['\"]", prompt)
    if tool_name == "echo" and m_quoted:
        return {"message": m_quoted.group(1)}
    if tool_name == "web_search":
        m = re.search(r"['\"](.+?)['\"]", prompt)
        return {"query": m.group(1) if m else "test"}
    m_url = re.search(r"https?://[^\s'\"]+", prompt)
    if tool_name in ("fetch_page", "fetch_page_deep") and m_url:
        return {"url": m_url.group(0)}
    if tool_name == "list_dir":
        m = re.search(r"['\"]([^'\"]+)['\"]", prompt)
        return {"path": m.group(1) if m else "."}
    if tool_name == "read_file":
        m = re.search(r"['\"]([^'\"]+\.(py|md|json|bat|sh|txt))['\"]", prompt)
        return {"path": m.group(1) if m else "README.md"}
    if tool_name == "walker_status":
        return {}
    if tool_name == "walker_task":
        m = re.search(r"['\"](.{20,}?)['\"]", prompt, re.DOTALL)
        return {"task": m.group(1) if m else prompt[:200]}
    if tool_name == "council_gozcu":
        m = re.search(r"['\"](.+?)['\"]", prompt)
        return {"task": m.group(1) if m else "test"}
    if tool_name == "council_teknisyen":
        m = re.search(r"['\"](.+?)['\"]", prompt)
        return {"task": m.group(1) if m else "test"}
    if tool_name == "deerflow_research":
        m = re.search(r"['\"](.+?)['\"]", prompt)
        return {"query": m.group(1) if m else "test"}
    if tool_name == "bridge_status":
        return {}
    if "chroma_list" in tool_name:
        return {}
    if "chroma_add" in tool_name:
        import time as _t
        uid = f"inq_{int(_t.time()) % 1000000}"
        return {"collection_name": "kuroshin_memory", "documents": ["Iron Inquisitor test"],
                "ids": [uid]}
    if "chroma_query" in tool_name:
        return {"collection_name": "kuroshin_memory", "query_texts": ["test"], "n_results": 1}
    return {}

# ─────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────

def run_test(test: dict) -> dict:
    t_start     = time.time()

    # ── Port check testi ──────────────────────────────────────────
    if test.get("type") == "port_check":
        port    = test["port"]
        host    = test.get("host", "127.0.0.1")
        is_open = port_open(host, port)
        status  = "PASS" if is_open else "FAIL"
        score   = test.get("weight", 1.0) if is_open else 0.0
        note    = "" if is_open else f"Port {port} kapalı — servis başlatılmamış (Kuroshin.bat [1])"
        output  = f"port_open({host}:{port}) = {is_open}"
        elapsed = round(time.time() - t_start, 2)
        return make_result(test, status, score, elapsed, output, note)

    # ── Security check testi (kılıç-kalkan simülasyonu) ───────────
    if test.get("type") == "security_check":
        import importlib.util, sys as _sys
        sec_path = str(BASE / "scripts" / "kuroshin_security.py")
        spec = importlib.util.spec_from_file_location("kuroshin_security", sec_path)
        sec  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sec)

        check_type     = test.get("check", "")       # command | injection | path_write | path_read
        inp            = test.get("input", "")
        expect_blocked = test.get("expect_blocked", True)

        if check_type == "command":
            allowed, reason = sec.check_command(inp)
            blocked = not allowed
            detail  = reason if not allowed else "izin verildi"
        elif check_type == "injection":
            clean, threat = sec.scan_for_injection(inp, source="test")
            blocked = not clean
            detail  = threat if not clean else "temiz"
        elif check_type == "path_write":
            allowed, reason = sec.check_path_write(inp)
            blocked = not allowed
            detail  = reason if not allowed else "izin verildi"
        elif check_type == "path_read":
            allowed, reason = sec.check_path_read(inp)
            blocked = not allowed
            detail  = reason if not allowed else "izin verildi"
        else:
            blocked = False
            detail  = f"Bilinmeyen check tipi: {check_type}"

        passed  = (blocked == expect_blocked)
        status  = "PASS" if passed else "FAIL"
        score   = test.get("weight", 1.0) if passed else 0.0
        exp_lbl = "BLOCKED" if expect_blocked else "ALLOWED"
        got_lbl = "BLOCKED" if blocked else "ALLOWED"
        note    = "" if passed else f"Beklenen: {exp_lbl} | Gerçek: {got_lbl} | {detail}"
        output  = f"{got_lbl}: {inp[:80]} → {detail}"
        elapsed = round(time.time() - t_start, 3)
        return make_result(test, status, score, elapsed, output, note)

    tool_server = test.get("tool", "")
    expect_tool = test.get("expect_tool_call", "")
    expect_str  = test.get("expect_contains", "")
    timeout     = test.get("timeout", 60)

    prompt      = test["prompt"]
    tool_result = ""
    tool_called = False

    if expect_tool and tool_server:
        args        = extract_args(prompt, expect_tool)
        tool_result = mcp_call(tool_server, expect_tool, args, timeout=timeout)
        # Araç yanıt döndürdüyse çağrı başarılı — chroma MCP hataları FAIL sayılır
        tool_called = not tool_result.startswith("ERROR: unknown") \
                      and not tool_result.startswith("TIMEOUT") \
                      and "Error executing tool" not in tool_result

    elapsed = round(time.time() - t_start, 1)

    if tool_result.startswith("TIMEOUT"):
        return make_result(test, "TIMEOUT", 0.0, elapsed, tool_result,
                           f"Zaman aşımı ({timeout}s)")

    # expect_contains boşsa → araç çağrılmış olması yeterli
    if not expect_str:
        passed = tool_called
    else:
        passed = expect_str.lower() in tool_result.lower()

    if not tool_called and expect_tool:
        status, score = "FAIL", 0.0
        note = f"Araç çağrısı başarısız: {tool_result[:120]}"
    elif passed:
        status, score = "PASS", 1.0 * test.get("weight", 1.0)
        note = ""
    else:
        status, score = "FAIL", 0.0
        note = f"'{expect_str}' bulunamadı. Sonuç: {tool_result[:120]}"

    return make_result(test, status, score, elapsed, tool_result[:400], note)

def make_result(test, status, score, elapsed, output, note):
    return {
        "id": test["id"], "tool": test.get("tool", ""),
        "category": test.get("category", ""), "status": status,
        "score": score, "weight": test.get("weight", 1.0),
        "elapsed": elapsed, "note": note, "output": output,
    }

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────

def send_telegram(msg: str):
    import socket, urllib.parse
    _orig = socket.getaddrinfo
    socket.getaddrinfo = lambda h, p, f=0, *a, **k: _orig(h, p, socket.AF_INET, *a, **k)
    try:
        env = (BASE / ".env").read_text(encoding="utf-8")
        t = re.search(r'TELEGRAM_TOKEN=(.+)', env)
        c = re.search(r'TELEGRAM_CHAT_ID=(.+)', env)
        if t and c:
            data = urllib.parse.urlencode({
                "chat_id": c.group(1).strip(),
                "text": msg, "parse_mode": "HTML"
            }).encode()
            urllib.request.urlopen(
                f"https://api.telegram.org/bot{t.group(1).strip()}/sendMessage",
                data, timeout=10
            )
    except Exception as e:
        print(f"[TG] {e}")
    finally:
        socket.getaddrinfo = _orig

# ─────────────────────────────────────────────
# RAPOR
# ─────────────────────────────────────────────

def build_report(results):
    total_w = sum(r["weight"] for r in results)
    earned  = sum(r["score"] for r in results)
    pct     = round(100 * earned / total_w, 1) if total_w else 0
    passes  = [r for r in results if r["status"] == "PASS"]
    fails   = [r for r in results if r["status"] != "PASS"]
    lines = [
        "<b>⚔️ Iron Inquisitor v5.2 — Self-Healing MCP Test</b>",
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"📊 <b>Puan: {earned:.1f}/{total_w:.1f} ({pct}%)</b>",
        f"✅ PASS: {len(passes)}  ❌ FAIL/TIMEOUT: {len(fails)}",
        "",
    ]
    if fails:
        lines.append("<b>🔴 Başarısız:</b>")
        for r in fails:
            lines.append(f"  [{r['status']}] {r['id']} — {r['note'][:90]}")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def _parse_args():
    """
    Desteklenen flagler:
      --suite <dosya>          Test suite JSON dosyası (varsayılan: test_suite_full_v2.json)
      --only <id1> <id2> ...   Sadece bu ID'leri çalıştır
      --category <cat> ...     Sadece bu kategorileri çalıştır
      --skip-passed            Son rapordaki PASS testleri atla (sadece FAIL/TIMEOUT çalıştır)
      --no-telegram            Telegram'a rapor gönderme
      --skip-llama             llama-server başlatma kontrolünü atla
      --skip-bridge            Servis başlatma adımını tamamen atla
    """
    args = sys.argv[1:]
    cfg = {
        "suite":       Path(__file__).parent / "test_suite_full_v2.json",
        "only":        [],
        "categories":  [],
        "skip_passed": "--skip-passed" in args,
        "no_telegram": "--no-telegram" in args,
        "skip_llama":  "--skip-llama"  in args,
        "skip_bridge": "--skip-bridge" in args,
    }
    i = 0
    while i < len(args):
        if args[i] == "--suite" and i + 1 < len(args):
            cfg["suite"] = Path(args[i + 1]); i += 2; continue
        if args[i] == "--only":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                cfg["only"].append(args[i]); i += 1
            continue
        if args[i] == "--category":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                cfg["categories"].append(args[i]); i += 1
            continue
        i += 1
    return cfg


def _last_passed_ids() -> set:
    """Son rapordaki PASS test ID'lerini döndür."""
    if not REPORT_DIR.exists():
        return set()
    reports = sorted(REPORT_DIR.glob("inquisitor_*.json"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return set()
    try:
        data = json.loads(reports[0].read_text(encoding="utf-8"))
        return {r["id"] for r in data if r.get("status") == "PASS"}
    except Exception:
        return set()


def main():
    cfg = _parse_args()

    all_tests = json.loads(cfg["suite"].read_text(encoding="utf-8"))

    # Filtrele
    tests = all_tests
    if cfg["only"]:
        id_set = set(cfg["only"])
        tests  = [t for t in tests if t["id"] in id_set]
        missing = id_set - {t["id"] for t in tests}
        if missing:
            print(f"[WARN] Bilinmeyen test ID'leri: {', '.join(missing)}")

    if cfg["categories"]:
        cat_set = set(cfg["categories"])
        tests   = [t for t in tests if t.get("category", "") in cat_set]

    if cfg["skip_passed"]:
        passed_ids = _last_passed_ids()
        skipped    = [t for t in tests if t["id"] in passed_ids]
        tests      = [t for t in tests if t["id"] not in passed_ids]
        if skipped:
            print(f"[SKIP] Son raporda PASS olan {len(skipped)} test atlandı: "
                  f"{', '.join(t['id'] for t in skipped)}")

    if not tests:
        print("[INQUISITOR v5.1] Çalıştırılacak test yok.")
        sys.exit(0)

    mode_note = ""
    if cfg["only"]:        mode_note = f" [--only: {', '.join(cfg['only'])}]"
    elif cfg["categories"]:mode_note = f" [--category: {', '.join(cfg['categories'])}]"
    elif cfg["skip_passed"]:mode_note = " [--skip-passed]"

    print(f"[INQUISITOR v5.1] Suite: {cfg['suite'].name}{mode_note}")
    print(f"[INQUISITOR v5.1] {len(tests)}/{len(all_tests)} test çalıştırılacak")

    if not cfg["skip_bridge"]:
        ensure_services(skip_llama=cfg["skip_llama"])

    REPORT_DIR.mkdir(exist_ok=True)
    results = []
    lock = threading.Lock()

    def run_and_print(test):
        result = run_test(test)
        icon = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏱️", "ERROR": "💥"}.get(
            result["status"], "?"
        )
        with lock:
            line = f"  [{result['id']}] {icon} {result['status']} ({result['elapsed']}s)"
            if result["note"]:
                line += f"\n      → {result['note']}"
            elif result["status"] == "PASS" and result["output"]:
                line += f"\n      ↳ {result['output'][:80]}"
            print(line)
        return result

    heavy_cats = {"web_fetch", "council"}
    light = [t for t in tests if t.get("category", "") not in heavy_cats]
    heavy = [t for t in tests if t.get("category", "") in heavy_cats]
    print(f"[INQUISITOR v5.1] {len(light)} hızlı (×4) + {len(heavy)} ağır (×2) paralel")

    with ThreadPoolExecutor(max_workers=4) as ex:
        for f in as_completed({ex.submit(run_and_print, t): t for t in light}):
            results.append(f.result())
    with ThreadPoolExecutor(max_workers=2) as ex:
        for f in as_completed({ex.submit(run_and_print, t): t for t in heavy}):
            results.append(f.result())

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rp = REPORT_DIR / f"inquisitor_{ts}.json"
    rp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    report_text = build_report(results)
    print("\n" + report_text.replace("<b>", "**").replace("</b>", "**"))
    if not cfg["no_telegram"]:
        send_telegram(report_text)

    passes  = sum(1 for r in results if r["status"] == "PASS")
    fails   = len(results) - passes
    fail_pct = round(100 * fails / len(results), 1) if results else 0
    if fail_pct > 30 and not cfg["no_telegram"]:
        send_telegram(
            f"🚨 <b>Kuroshin Kalite Alarmı</b>\n"
            f"Başarısız test oranı %30 eşiğini aştı!\n"
            f"❌ {fails}/{len(results)} test başarısız (%{fail_pct})\n"
            f"⚠️ Sistem durumu incelenmeli."
        )

    print(f"\n[INQUISITOR v5.1] Rapor: {rp}")
    sys.exit(0 if passes == len(tests) else 1)

if __name__ == "__main__":
    main()
