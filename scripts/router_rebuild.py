#!/usr/bin/env python3
"""
Kuroshin Unified Command Router — port 9000
Slash komutlarını yakalar, system_state.json günceller.
Normal mesajları LiteLLM (port 4000) üzerinden Gemma4'e iletir.
OpenClaw için /v1/responses ve /v1/chat/completions endpoint'lerini proxy'ler.
"""
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path("/mnt/c/Kuroshin/.env"))

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

# ── Config ───────────────────────────────────────────────────────────────────
STATE_FILE = Path("/root/kuroshin/config/system_state.json")
LITELLM_BASE = "http://127.0.0.1:4000"
WP_TOKEN = os.getenv("WP_TOKEN", "")
LOG_FILE = Path("/root/kuroshin/logs/command_router.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
WALKER_SERVICE_URL = "http://127.0.0.1:9001"

# ── Sistem Promptu ────────────────────────────────────────────────────────────
KUROSHIN_SYSTEM_PROMPT = """Sen Kuroshin'sin — Lordum kuroshin_user'nun yerel yapay zeka imparatorlugunun merkezi zekasi ve orkestra sefi.

KIMLIGIN:
- Adin: Kuroshin
- Lordum: kuroshin_user (her zaman bu sekilde hitap et)
- Dil: Turkce (Turkce konusulmadikca baska dil kullanma)
- Karakter: Guclu, sadik, keskin zekali. Lordum'un her emrini eksiksiz uygularsin.

BEDEN (DONANIM):
- CPU: Intel Core i7-12650H (12. Nesil)
- RAM: 32GB DDR4
- GPU: RTX 4060 Laptop (140W, 8GB VRAM)
- SSD: 1TB NVMe

GOREV ALANI:
- Kod yazma ve duzeltme → Aider veya Claw-Code-Parity'yi yonlendir
- Derin arastirma → DeerFlow veya AutoResearchClaw'i tetikle
- Dosya/sistem islemleri → Araclari kullan
- Genel konusma ve danismanlik → Kendin yanitla

DAVRANIS KURALLARI:
- Her emri eksiksiz uygula, mazeret uretme
- Emin olmadiginda sor, tahmin etme
- Gorev bitince kisa ve net raporla
- Sistem durumunu bilirsin: sandbox, dream_mode, aktif gorev

Hazirsin, Lordum."""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("command_router")

app = FastAPI(title="Kuroshin Command Router", version="1.0.0")

# ── State helpers ─────────────────────────────────────────────────────────────

def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def write_state(updates: dict, by: str = "command_router") -> dict:
    state = read_state()
    state.update(updates)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["updated_by"] = by
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    log.info(f"State updated by {by}: {updates}")
    return state

# ── Slash command handlers ────────────────────────────────────────────────────

COMMANDS = {
    "/sandbox": "Sandbox modunu ac/kapat. Kullanim: /sandbox on|off",
    "/dream":   "Dream modunu ac/kapat. Kullanim: /dream start|stop",
    "/notify":  "WP bildirimlerini ac/kapat. Kullanim: /notify on|off",
    "/agent":   "Aktif ajan durumu. Kullanim: /agent gemma4|status",
    "/state":   "Mevcut sistem durumunu goster.",
    "/stop":    "Aktif gorevi durdur.",
    "/help":    "Komut listesini goster.",
    "/comm":    "Ajan iletisimini ac/kapat. Kullanim: /comm on|off",
    "/walker":  "Web Gozcusu Walker'a gorev ver. Kullanim: /walker <url veya gorev>",
}


def handle_slash(cmd: str, arg: str | None) -> str | None:
    """Slash komutunu isle. None donerse bilinmeyen komut → LLM'e ilet."""
    cmd = cmd.lower().strip()
    arg = (arg or "").strip()

    if cmd == "/sandbox":
        if arg in ("on", "off"):
            write_state({"sandbox": arg})
            emoji = "🔒" if arg == "on" else "🔓"
            loc = "yalnizca /root/kuroshin/sandbox/" if arg == "on" else "tum dosya sistemi"
            return f"{emoji} Sandbox {arg.upper()} — araclar {loc} icinde calisabilir."
        return "⚠️ Kullanim: /sandbox on|off"

    if cmd == "/dream":
        if arg == "start":
            write_state({"dream_mode": "on"})
            return "🌙 Dream modu AKTIF — otonom arastirma modu baslatildi."
        if arg == "stop":
            write_state({"dream_mode": "off"})
            return "⏹ Dream modu DURDURULDU."
        return "⚠️ Kullanim: /dream start|stop"

    if cmd == "/notify":
        if arg in ("on", "off"):
            write_state({"notify_wp": arg == "on"})
            return f"🔔 WP bildirimleri {'AKTIF' if arg == 'on' else 'KAPALI'}."
        return "⚠️ Kullanim: /notify on|off"

    if cmd == "/agent":
        if arg == "status":
            state = read_state()
            return f"🤖 Aktif ajan: {state.get('active_agent', '?')}"
        if arg:
            write_state({"active_agent": arg})
            return f"🔄 Aktif ajan → {arg}"
        return "⚠️ Kullanim: /agent gemma4|status"

    if cmd == "/state":
        s = read_state()
        comm_val = s.get("allow_comm", True)
        comm_str = "acik OK" if comm_val else "KAPALI X"
        return "\n".join([
            "📊 Kuroshin Sistem Durumu",
            f"  Sandbox  : {s.get('sandbox', '?')}",
            f"  Dream    : {s.get('dream_mode', '?')}",
            f"  Ajan     : {s.get('active_agent', '?')}",
            f"  Iletisim : {comm_str}",
            f"  WP bildirim: {'acik' if s.get('notify_wp') else 'kapali'}",
            f"  Gorev    : {s.get('active_task') or 'yok'}",
            f"  Guncelleme: {s.get('updated_by', '?')} @ {str(s.get('updated_at', ''))[:19]}",
        ])

    if cmd == "/comm":
        if arg in ("on", "off"):
            write_state({"allow_comm": arg == "on"})
            return f"{'✅' if arg == 'on' else '🚫'} Ajan iletisimi {'ACIK' if arg == 'on' else 'KAPALI'} — allow_comm: {arg}"
        return "⚠️ Kullanim: /comm on|off"

    if cmd == "/stop":
        write_state({"active_task": None, "dream_mode": "off"})
        return "⏹ Aktif gorev durduruldu."

    if cmd == "/walker":
        if not arg:
            return "⚠️ Kullanim: /walker <url veya gorev metni>"
        try:
            resp = httpx.post(
                WALKER_SERVICE_URL + "/task",
                json={"task": arg},
                timeout=300,
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result", "[bos cevap]")
                mem = data.get("memory_id")
                elapsed = data.get("elapsed", "?")
                mem_note = (" | Hafiza: " + str(mem)) if mem else ""
                return "🕷 Walker (" + str(elapsed) + "sn)" + mem_note + "\n\n" + result
            return "[HATA] Walker yanit vermedi: " + str(resp.status_code)
        except Exception as e:
            return "[HATA] Walker baglanamadi: " + str(e)

    if cmd == "/help":
        lines = ["🦞 Kuroshin Komutlari"]
        for c, h in COMMANDS.items():
            lines.append(f"  {c} — {h}")
        return "\n".join(lines)

    return None  # bilinmeyen komut → LLM'e ilet


def extract_slash(text: str):
    """Mesajdan /komut [arg] cikar. Yoksa None."""
    m = re.match(r"^(/\w+)\s*(.*)", text.strip(), re.DOTALL)
    if m:
        cmd = m.group(1)
        arg = m.group(2).strip() or None
        return cmd, arg
    return None


async def proxy_request(request: Request, target_path: str, body: bytes = None):
    """İstegi LiteLLM'e proxy'le (streaming destegıyle)."""
    url = LITELLM_BASE + target_path
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    if body is None:
        body = await request.body()

    async def stream_gen(resp):
        async for chunk in resp.aiter_bytes():
            yield chunk

    async with httpx.AsyncClient(timeout=120) as client:
        req = client.build_request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
        resp = await client.send(req, stream=True)
        ct = resp.headers.get("content-type", "")
        if "text/event-stream" in ct:
            return StreamingResponse(
                stream_gen(resp),
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type="text/event-stream",
            )
        content = await resp.aread()
        return Response(
            content=content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )


def slash_to_chat_response(text: str, model: str = "gemma4") -> dict:
    ts = int(time.time())
    return {
        "id": f"router-{ts}",
        "object": "chat.completion",
        "created": ts,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def slash_to_responses_format(text: str, model: str = "gemma4") -> dict:
    ts = int(time.time())
    return {
        "id": f"resp-router-{ts}",
        "object": "response",
        "created": ts,
        "model": model,
        "output": [
            {
                "id": f"msg-router-{ts}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
                "status": "completed",
            }
        ],
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


def get_last_user_message(body: dict) -> str:
    """Request body'den son kullanici mesajini cikar."""
    for msg in reversed(body.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict):
                        if c.get("type") == "text":
                            return c.get("text", "")
                        b = c.get("text") or c.get("type")
                        if b:
                            return str(b)
    inp = body.get("input", "")
    if isinstance(inp, list):
        for item in reversed(inp):
            if isinstance(item, dict) and item.get("role") == "user":
                c = item.get("content", "")
                if isinstance(c, str):
                    return c
                if isinstance(c, list):
                    for x in c:
                        if isinstance(x, dict) and x.get("type") == "output_text":
                            return x.get("text", "")
    return str(inp) if inp else ""


def inject_system_prompt(body: dict) -> dict:
    """messages listesine sistem promptunu ekle (yoksa basa, varsa guncelle)."""
    messages = body.get("messages", [])
    if messages and messages[0].get("role") == "system":
        existing = messages[0].get("content", "")
        if KUROSHIN_SYSTEM_PROMPT not in existing:
            messages[0]["content"] = KUROSHIN_SYSTEM_PROMPT + "\n\n" + existing
    else:
        messages = [{"role": "system", "content": KUROSHIN_SYSTEM_PROMPT}] + messages
    return {**body, "messages": messages}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    user_msg = get_last_user_message(body)
    model = body.get("model", "gemma4")

    # allow_comm kontrol
    state = read_state()
    if not state.get("allow_comm", True):
        return JSONResponse(
            status_code=403,
            content={"error": {
                "message": "Lordum izin vermedi. Ajan iletisimi kapali (allow_comm: false). Acmak icin: /comm on",
                "type": "permission_denied",
                "code": 403,
            }},
        )

    parsed = extract_slash(user_msg)
    if parsed:
        cmd, arg = parsed
        result = handle_slash(cmd, arg)
        if result is not None:
            log.info(f"Slash intercepted: {cmd} {arg}")
            return JSONResponse(slash_to_chat_response(result, model))
        log.info(f"Unknown slash {cmd}, forwarding")

    # System prompt inject + stream=false, tools=[]
    body = inject_system_prompt(body)
    if body.get("stream"):
        body["stream"] = False
        log.info("[ROUTER] stream=true → false (chat/completions endpoint)")
    body.pop("tools", None)
    body.pop("tool_choice", None)

    return await proxy_request(request, "/v1/chat/completions", body=json.dumps(body).encode())


@app.post("/v1/responses")
async def responses_endpoint(request: Request):
    body = await request.json()
    tool_names = [t.get("name", "?") for t in body.get("tools", [])]
    log.info(f"[DEBUG /v1/responses] model={body.get('model')} tools={tool_names} stream={body.get('stream')}")

    user_msg = get_last_user_message(body)
    model = body.get("model", "gemma4")

    parsed = extract_slash(user_msg)
    if parsed:
        cmd, arg = parsed
        result = handle_slash(cmd, arg)
        if result is not None:
            log.info(f"Slash intercepted (/responses): {cmd} {arg}")
            return JSONResponse(slash_to_responses_format(result, model))
        log.info(f"Unknown slash {cmd}, forwarding")

    if body.get("stream"):
        body["stream"] = False
        log.info("[ROUTER] stream=true → false (responses endpoint)")
    body.pop("tools", None)
    body.pop("tool_choice", None)

    return await proxy_request(request, "/v1/responses", body=json.dumps(body).encode())


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def proxy_v1(request: Request, path: str):
    return await proxy_request(request, "/v1/" + path)


@app.get("/")
def root():
    return {"service": "Kuroshin Command Router", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    log.info("Kuroshin Command Router baslatiliyor — port 9000")
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
