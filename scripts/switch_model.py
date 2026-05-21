"""
Kuroshin Model Switch v2.0
==========================
Llama-server'i durdurur, yeni modelle yeniden baslatir.
Tek merkezli model katalogu saglar; TUI ve diger araclar bunu kullanir.

Kullanim:
  python3 switch_model.py list
  python3 switch_model.py status
  python3 switch_model.py current [--json|--plain]
  python3 switch_model.py options [--json]
  python3 switch_model.py history
  python3 switch_model.py switch <model_adi_veya_yolu> [--json]
"""

import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path("/mnt/c/Kuroshin")
MODELS_DIR = Path("/root/kuroshin/models")
MODELS_DIR_WIN = BASE_DIR / "models"
HISTORY_FILE = BASE_DIR / "memory" / "model_history.json"
LOG_FILE = BASE_DIR / "logs" / "model_switch.log"
STATE_FILE = BASE_DIR / "memory" / "active_model.json"
CLI_JSON_MODE = False

LLAMA_URL = "http://127.0.0.1:8080"
LLAMA_BIN = "/root/kuroshin/engines/llama.cpp/build/bin/llama-server"

MODEL_CONTEXT = {
    "1.2b": 32768,
    "1.5b": 32768,
    "3b": 65536,
    "4b": 131072,
    "7b": 65536,
    "8b": 32768,
    "14b": 16384,
    "30b": 16384,
    "35b": 16384,
    "a3b": 16384,
}

MODEL_HINTS = [
    {
        "match": "qwen3-8b-abliterated",
        "label": "Qwen3-8B abliterated Q5_K_M",
        "aliases": ["qwen3", "qwen3-abliterated", "qwen3-8b", "main"],
    },
    {
        "match": "huihui-qwen3.6-35b-a3b",
        "label": "Huihui-Qwen3.6-35B-A3B abliterated IQ4_XS (MoE)",
        "aliases": ["qwen3.6", "qwen36", "35b-a3b", "a3b", "moe", "huihui"],
    },
    {
        "match": "qwen3.6-35b-a3b",
        "label": "Qwen3.6-35B-A3B MoE",
        "aliases": ["qwen3.6", "qwen36", "35b-a3b", "a3b", "moe"],
    },
    {
        "match": "qwen2.5-coder",
        "label": "Qwen2.5-Coder",
        "aliases": ["qwen2.5", "qwen-coder", "coder"],
    },
    {
        "match": "thinking-claude",
        "label": "Thinking-Claude 1.2B",
        "aliases": ["thinking", "thinking-claude", "claude-1.2b"],
    },
    {
        "match": "gemma",
        "label": "Gemma",
        "aliases": ["gemma", "gemma4"],
    },
]


def _log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, file=sys.stderr if CLI_JSON_MODE else sys.stdout)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _load_history() -> list:
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_history(history: list):
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        _log(f"Gecmis kayit hatasi: {e}")


def _read_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _write_state(payload: dict):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        _log(f"State yazma hatasi: {e}")


def unique_preserve(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        normalized = (item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _is_moe(model_name: str) -> bool:
    lower = model_name.lower()
    return any(tok in lower for tok in ("a3b", "-ax", "moe"))


def _get_context_size(model_name: str) -> int:
    name_lower = model_name.lower()
    for key, ctx in sorted(MODEL_CONTEXT.items(), key=lambda x: -len(x[0])):
        if key in name_lower:
            return ctx
    return 65536


def _format_ctx(ctx: int) -> str:
    if ctx % 1024 == 0:
        return f"{ctx // 1024}K"
    return str(ctx)


def _model_hint(model_name: str) -> dict:
    lower = model_name.lower()
    for hint in MODEL_HINTS:
        if hint["match"] in lower:
            return hint
    stem = Path(model_name).stem
    return {
        "label": stem.replace("_", " ").replace("-", " "),
        "aliases": [stem.lower().replace("_", "-")],
    }


def _describe_model(path: Path, active_name: str = "") -> dict:
    hint = _model_hint(path.name)
    ctx = _get_context_size(path.name)
    size_gb = round(path.stat().st_size / (1024 ** 3), 2)
    aliases = unique_preserve([
        *(hint.get("aliases", []) or []),
        path.stem.lower().replace("_", "-"),
    ])
    description = f"{size_gb} GB · {_format_ctx(ctx)} ctx"
    if aliases:
        description += f" · aliases: {', '.join(aliases)}"
    active = path.name == active_name
    if active:
        description += " · ACTIVE"
    return {
        "name": path.name,
        "value": path.name,
        "path": str(path),
        "label": hint.get("label", path.name),
        "description": description,
        "size_gb": size_gb,
        "context_size": ctx,
        "aliases": aliases,
        "active": active,
    }


def get_active_model() -> str:
    try:
        import urllib.request

        with urllib.request.urlopen(f"{LLAMA_URL}/v1/models", timeout=3) as r:
            data = json.loads(r.read())
            models = data.get("data", [])
            if models:
                return models[0].get("id", "bilinmiyor")
    except Exception:
        pass

    try:
        result = subprocess.run(
            [
                "bash",
                "-c",
                (
                    "ps aux | grep llama-server | grep -v grep | "
                    "awk '{for(i=1;i<=NF;i++) if($i==\"-m\") print $(i+1)}' | head -1"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        path = result.stdout.strip()
        if path:
            return Path(path).name
    except Exception:
        pass
    return "bilinmiyor"


def list_models() -> list[dict]:
    models = []
    active = get_active_model()
    seen = set()
    for scan_dir in (MODELS_DIR, MODELS_DIR_WIN):
        if not scan_dir.exists():
            continue
        for file_path in sorted(scan_dir.glob("*.gguf")):
            if file_path.name in seen:
                continue
            seen.add(file_path.name)
            models.append(_describe_model(file_path, active))
    return models


def get_active_model_payload() -> dict:
    active = get_active_model()
    state = _read_state()
    models = list_models()
    active_meta = next((m for m in models if m["name"] == active), None)
    return {
        "active_model": active,
        "label": active_meta["label"] if active_meta else state.get("label", active),
        "path": active_meta["path"] if active_meta else state.get("path", ""),
        "context_size": (
            active_meta["context_size"]
            if active_meta
            else state.get("context_size")
        ),
        "size_gb": active_meta["size_gb"] if active_meta else state.get("size_gb"),
        "aliases": active_meta["aliases"] if active_meta else state.get("aliases", []),
    }


def _resolve_model_path(target: str, models: list[dict]) -> str | None:
    if Path(target).exists():
        return target

    normalized = target.lower().replace(" ", "").replace("-", "").replace("_", "")
    for model in models:
        name_norm = model["name"].lower().replace("-", "").replace("_", "")
        label_norm = model["label"].lower().replace(" ", "").replace("-", "").replace("_", "")
        alias_norms = [
            alias.lower().replace(" ", "").replace("-", "").replace("_", "")
            for alias in model.get("aliases", [])
        ]
        if (
            normalized in name_norm
            or normalized in label_norm
            or normalized in alias_norms
        ):
            return model["path"]
    return None


def stop_llama() -> bool:
    _log("Llama-server durduruluyor...")
    try:
        subprocess.run(
            ["bash", "-c", "pkill -9 -f llama-server; fuser -k 8080/tcp 2>/dev/null; sleep 1"],
            timeout=10,
        )
        _log("Llama-server durduruldu.")
        return True
    except Exception as e:
        _log(f"Durdurma hatasi: {e}")
        return False


def start_llama(model_path: str) -> bool:
    model_name = Path(model_path).name
    ctx = _get_context_size(model_name)
    if _is_moe(model_name):
        extra = '-ot "exps=CPU"'
    else:
        extra = "--spec-type ngram-cache --draft-max 16 --draft-min 2 --draft-p-min 0.7"
    cmd = (
        f"source /root/kuroshin/venv/bin/activate; "
        f"nohup {LLAMA_BIN} -m {model_path} "
        f"--host 0.0.0.0 --port 8080 -ngl 99 -c {ctx} -fa on "
        f"-ctk q4_0 -ctv q4_0 --embeddings --mlock --no-mmap "
        f"{extra} "
        f"> /root/kuroshin/logs/llama-server.log 2>&1 &"
    )
    _log(f"Baslatiliyor: {Path(model_path).name} (ctx={ctx})")
    try:
        subprocess.Popen(["bash", "-c", cmd])
        for i in range(45):
            time.sleep(2)
            try:
                import urllib.request

                with urllib.request.urlopen(f"{LLAMA_URL}/health", timeout=2) as r:
                    if r.status == 200:
                        _log(f"Llama-server hazir ({(i + 1) * 2}s)")
                        return True
            except Exception:
                pass
        _log("Llama-server 90s icinde yanit vermedi.")
        return False
    except Exception as e:
        _log(f"Baslatma hatasi: {e}")
        return False


def _speed_test() -> float:
    try:
        import urllib.request

        payload = json.dumps(
            {
                "model": get_active_model(),
                "messages": [{"role": "user", "content": "1'den 20'ye kadar say."}],
                "max_tokens": 50,
                "temperature": 0.1,
            }
        ).encode()
        t0 = time.time()
        req = urllib.request.Request(
            f"{LLAMA_URL}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            elapsed = time.time() - t0
            tokens = data.get("usage", {}).get("completion_tokens", 0)
            return round(tokens / elapsed, 1) if elapsed > 0 else 0.0
    except Exception:
        return 0.0


def switch_model(target: str) -> dict:
    previous_model = get_active_model()
    _log(f"Gecis basliyor: {previous_model} -> {target}")

    models = list_models()
    model_path = _resolve_model_path(target, models)
    if not model_path:
        available = ", ".join(m["name"] for m in models) if models else "yok"
        return {
            "ok": False,
            "mesaj": f"Model bulunamadi: '{target}'\nMevcut modeller: {available}",
        }

    model_name = Path(model_path).name
    if not stop_llama():
        return {"ok": False, "mesaj": "Llama-server durdurulamadi."}

    started = start_llama(model_path)
    tok_s = _speed_test() if started else 0.0
    if started:
        _log(f"Hiz testi: {tok_s} tok/s")

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    active_meta = _describe_model(Path(model_path), model_name)

    history = _load_history()
    history.append(
        {
            "ts": ts,
            "onceki": previous_model,
            "yeni": model_name,
            "yol": model_path,
            "tok_s": tok_s,
            "basarili": started,
        }
    )
    _save_history(history[-20:])

    _write_state(
        {
            "ts": ts,
            "active_model": model_name,
            "label": active_meta["label"],
            "path": model_path,
            "context_size": active_meta["context_size"],
            "size_gb": active_meta["size_gb"],
            "aliases": active_meta["aliases"],
            "tok_s": tok_s,
        }
    )

    if started:
        return {
            "ok": True,
            "mesaj": (
                f"Model degistirildi.\n"
                f"{previous_model} -> {model_name}\n"
                f"Hiz: {tok_s} tok/s"
            ),
            "onceki": previous_model,
            "yeni": model_name,
            "tok_s": tok_s,
            "label": active_meta["label"],
            "active_model": model_name,
        }

    return {
        "ok": False,
        "mesaj": (
            f"Model baslatilamadi: {model_name}\n"
            f"Onceki model ({previous_model}) artik kapali. /bat ile sistemi yeniden baslatin."
        ),
        "onceki": previous_model,
        "yeni": model_name,
        "label": active_meta["label"],
        "active_model": model_name,
    }


def cmd_list():
    active = get_active_model()
    models = list_models()
    print(f"Aktif model: {active}")
    print(f"Kullanilabilir modeller ({len(models)}):")
    for model in models:
        marker = "->" if model["name"] == active else "  "
        print(f"{marker} {model['label']} [{model['name']}] ({model['size_gb']} GB)")


def cmd_status():
    active = get_active_model()
    history = _load_history()
    last = history[-1] if history else {}
    print(f"Aktif model: {active}")
    if last:
        print(
            f"Son gecis: {last.get('ts', '')} | "
            f"{last.get('onceki', '')} -> {last.get('yeni', '')} | "
            f"{last.get('tok_s', 0)} tok/s"
        )
    print(f"Su an hiz: {_speed_test()} tok/s")


def cmd_history():
    history = _load_history()
    if not history:
        print("Gecmis yok.")
        return
    for item in reversed(history[-5:]):
        status = "OK" if item["basarili"] else "FAIL"
        print(
            f"[{item['ts']}] {item['onceki']} -> {item['yeni']} | "
            f"{item['tok_s']} tok/s | {status}"
        )


def cmd_current(json_mode: bool = False, plain: bool = False):
    payload = get_active_model_payload()
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False))
    elif plain:
        aliases = payload.get("aliases", [])
        print(aliases[0] if aliases else payload["active_model"])
    else:
        print(payload["active_model"])


def cmd_options(json_mode: bool = False):
    payload = {
        "active_model": get_active_model(),
        "options": [
            {
                "value": model["name"],
                "label": model["label"],
                "description": model["description"],
                "aliases": model["aliases"],
                "size_gb": model["size_gb"],
                "context_size": model["context_size"],
                "active": model["active"],
            }
            for model in list_models()
        ],
    }
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(f"Aktif model: {payload['active_model']}")
    for option in payload["options"]:
        marker = "->" if option["active"] else "  "
        print(f"{marker} {option['label']} [{option['value']}]")


if __name__ == "__main__":
    raw_args = sys.argv[1:]
    if not raw_args:
        print(__doc__)
        sys.exit(0)

    json_mode = "--json" in raw_args
    CLI_JSON_MODE = json_mode
    plain_mode = "--plain" in raw_args
    raw_args = [arg for arg in raw_args if arg not in ("--json", "--plain")]
    if not raw_args:
        print(__doc__)
        sys.exit(0)

    cmd = raw_args[0].lower()

    if cmd == "list":
        cmd_list()
    elif cmd == "status":
        cmd_status()
    elif cmd == "current":
        cmd_current(json_mode=json_mode, plain=plain_mode)
    elif cmd == "options":
        cmd_options(json_mode=json_mode)
    elif cmd == "history":
        cmd_history()
    elif cmd == "switch" and len(raw_args) >= 2:
        target = " ".join(raw_args[1:])
        result = switch_model(target)
        if json_mode:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(result["mesaj"])
        sys.exit(0 if result["ok"] else 1)
    else:
        print(f"Bilinmeyen komut: {cmd}")
        print("Kullanim: switch_model.py [list|status|current|options|history|switch <model>] [--json|--plain]")
        sys.exit(1)
