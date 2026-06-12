"""
Bridge broadcast test: ws://localhost:9003'e bağlan, mesaj bekle.
Çalıştır → "WAITING" görünce başka terminalde alarm_run.py --test-bridge at.
"""
import asyncio
import websockets
import json

async def main():
    print("Bağlanıyor ws://localhost:9003 ...")
    try:
        async with websockets.connect('ws://localhost:9003', open_timeout=5) as ws:
            print("CONNECTED — mesaj bekleniyor (15sn timeout)...")
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(raw)
                print(f"✅ RECEIVED: type={data.get('type')} text={data.get('text','')[:60]}")
            except asyncio.TimeoutError:
                print("❌ TIMEOUT: 15sn içinde broadcast gelmedi — bridge _broadcast çalışmıyor")
    except Exception as e:
        print(f"❌ BAĞLANTI HATASI: {type(e).__name__}: {e}")

asyncio.run(main())
