"""
Kuroshin Bridge — Windows :9003 WebSocket hub
Chancellor WSL :9005 SSE → WS broadcast → UI
UI → WS → Chancellor :9005 POST /message
"""
import asyncio
import http.client
import json
import threading

import websockets


_WS_CLIENTS: set                      = set()
_BRIDGE_LOOP: asyncio.AbstractEventLoop = None


# ── WebSocket handler ─────────────────────────────────────────────────────────

async def _ws_handler(websocket):
    _WS_CLIENTS.add(websocket)
    try:
        async for msg in websocket:
            try:
                data = json.loads(msg)
                if data.get('type') == 'user_message':
                    _forward_to_chancellor(data.get('text', ''))
                elif data.get('type') in ('alarm', 'status', 'chat', 'processing', 'done'):
                    # Harici push (alarm.py gibi) → UI'ya broadcast
                    await _broadcast(data)
            except Exception:
                pass
    finally:
        _WS_CLIENTS.discard(websocket)


async def _broadcast(payload: dict):
    if not _WS_CLIENTS:
        return
    text = json.dumps(payload, ensure_ascii=False)
    dead = set()
    for ws in list(_WS_CLIENTS):
        try:
            await ws.send(text)
        except Exception:
            dead.add(ws)
    _WS_CLIENTS -= dead


# ── Chancellor → UI iletim ────────────────────────────────────────────────────

async def _sse_poller():
    """
    Chancellor :9005/stream SSE'yi raw asyncio socket ile dinler.
    Yeni mesaj gelince WS istemcilerine broadcast eder.
    aiohttp bağımlılığı gerektirmez (Windows'ta saf stdlib).
    """
    while True:
        try:
            reader, writer = await asyncio.open_connection('localhost', 9005)
            req = (
                b'GET /stream HTTP/1.1\r\n'
                b'Host: localhost:9005\r\n'
                b'Accept: text/event-stream\r\n'
                b'Connection: keep-alive\r\n\r\n'
            )
            writer.write(req)
            await writer.drain()

            # HTTP header'larını atla
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10)
                if not line or line == b'\r\n':
                    break

            buf = b''
            while True:
                chunk = await asyncio.wait_for(reader.read(512), timeout=60)
                if not chunk:
                    break
                buf += chunk
                while b'\n\n' in buf:
                    ev, buf = buf.split(b'\n\n', 1)
                    for ln in ev.split(b'\n'):
                        if ln.startswith(b'data: '):
                            raw = ln[6:].decode('utf-8', errors='replace').strip()
                            try:
                                payload = json.loads(raw)
                                await _broadcast(payload)
                            except Exception:
                                pass

            writer.close()
            await writer.wait_closed()

        except Exception:
            await asyncio.sleep(5)  # bağlantı koptu / chancellor henüz başlamadı


# ── UI → Chancellor ───────────────────────────────────────────────────────────

def _forward_to_chancellor(text: str):
    """UI'dan gelen mesajı chancellor'a POST /message ile gönderir."""
    try:
        conn = http.client.HTTPConnection('localhost', 9005, timeout=5)
        body = json.dumps({'text': text}).encode()
        conn.request('POST', '/message', body, {'Content-Type': 'application/json'})
        conn.getresponse()
        conn.close()
    except Exception:
        pass


# ── Başlatma ──────────────────────────────────────────────────────────────────

def start():
    """
    kuroshin_floating_ui/main.py'den daemon thread olarak çağrılır.
    WS :9003 + SSE poller aynı event loop'ta çalışır.
    """
    def _run():
        global _BRIDGE_LOOP
        loop = asyncio.new_event_loop()
        _BRIDGE_LOOP = loop
        asyncio.set_event_loop(loop)

        async def _serve():
            async with websockets.serve(_ws_handler, 'localhost', 9003):
                asyncio.create_task(_sse_poller())
                await asyncio.Future()   # run forever

        loop.run_until_complete(_serve())

    threading.Thread(target=_run, name='bridge', daemon=True).start()
