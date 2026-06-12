"""
Kuroshin Chancellor HTTP Mini Server — WSL :9005
aiohttp: GET /health + GET /status + POST /message + GET /stream (SSE)
Kullanım: kuroshin_chancellor.py main() içinde start() çağrılır.
          push_to_sse(type, text) herhangi thread'den güvenli çağrılabilir.
"""
import asyncio
import json
import time
import threading
import urllib.request

from aiohttp import web

_SSE_CLIENTS: set   = set()
_LOOP: asyncio.AbstractEventLoop = None
_MSG_CALLBACK                    = None  # UI mesajı → chancellor'a ilet


# ── Endpoint'ler ──────────────────────────────────────────────────────────────

async def _health(req):
    return web.json_response({'ok': True, 'service': 'chancellor', 'ts': time.time()})


async def _status(req):
    lm_ok = wk_ok = False
    try:
        urllib.request.urlopen('http://localhost:8080/health', timeout=1)
        lm_ok = True
    except Exception:
        pass
    try:
        urllib.request.urlopen('http://localhost:9002/health', timeout=1)
        wk_ok = True
    except Exception:
        pass
    return web.json_response({'ch': True, 'lm': lm_ok, 'wk': wk_ok})


async def _message(req):
    try:
        data = await req.json()
        text = str(data.get('text', '')).strip()
        if text and _MSG_CALLBACK:
            threading.Thread(target=_MSG_CALLBACK, args=(text,), daemon=True).start()
        return web.json_response({'ok': True})
    except Exception as e:
        return web.json_response({'ok': False, 'error': str(e)}, status=400)


async def _stream(req):
    """SSE endpoint — her SSE istemcisine push için asyncio.Queue kullanılır."""
    resp = web.StreamResponse(headers={
        'Content-Type':  'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection':    'keep-alive',
        'Access-Control-Allow-Origin': '*',
    })
    await resp.prepare(req)

    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _SSE_CLIENTS.add(q)
    try:
        while True:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=25)
                data    = json.dumps(payload, ensure_ascii=False)
                await resp.write(f'data: {data}\n\n'.encode())
            except asyncio.TimeoutError:
                # heartbeat — proxy timeout'unu önle
                await resp.write(b': heartbeat\n\n')
    except (ConnectionResetError, asyncio.CancelledError, Exception):
        pass
    finally:
        _SSE_CLIENTS.discard(q)
    return resp


# ── SSE broadcast ─────────────────────────────────────────────────────────────

async def _broadcast_all(payload: dict):
    for q in list(_SSE_CLIENTS):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def push_to_sse(msg_type: str, text: str, extra: dict = None):
    """
    Chancellor herhangi thread'inden çağrılır.
    msg_type: 'chat' | 'processing' | 'done' | 'alarm' | 'status'
    """
    if not _LOOP or not _SSE_CLIENTS:
        return
    payload = {'type': msg_type, 'text': text}
    if extra:
        payload.update(extra)
    asyncio.run_coroutine_threadsafe(_broadcast_all(payload), _LOOP)


# ── Başlatma ──────────────────────────────────────────────────────────────────

def start(msg_callback=None):
    """
    main.py'den daemon thread olarak çağrılır.
    msg_callback(text: str) — UI'dan gelen mesaj işleyici.
    """
    global _MSG_CALLBACK

    _MSG_CALLBACK = msg_callback

    def _run():
        global _LOOP
        loop = asyncio.new_event_loop()
        _LOOP = loop
        asyncio.set_event_loop(loop)

        app = web.Application()
        app.router.add_get('/health',   _health)
        app.router.add_get('/status',   _status)
        app.router.add_post('/message', _message)
        app.router.add_get('/stream',   _stream)

        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, '0.0.0.0', 9005)
        loop.run_until_complete(site.start())
        loop.run_forever()

    threading.Thread(target=_run, name='chancellor-http', daemon=True).start()
