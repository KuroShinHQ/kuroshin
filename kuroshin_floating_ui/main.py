"""
Kuroshin Floating UI — Ana giriş noktası
Başlatma: pythonw main.py [--mode lite|full_power]
"""
import sys
import os
import json
import threading
import argparse

HERE         = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(HERE, 'settings.json')
WEB_DIR       = os.path.join(HERE, 'web')
ICON_PATH     = os.path.join(HERE, 'assets', 'icon.ico')

sys.path.insert(0, HERE)

import webview
import pystray
from PIL import Image, ImageDraw

from api   import KuroshinAPI
from modes import ModeManager


def _load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            'orb_x': 1812, 'orb_y': 972,
            'orb_corner': 'bottom-right',
            'mode': 'lite', 'panel_open': False,
            'opacity': 0.92, 'theme': 'dark',
        }


def _make_icon() -> Image.Image:
    try:
        return Image.open(ICON_PATH).convert('RGBA')
    except Exception:
        # Basit daire ikon (icon.ico yokken)
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d   = ImageDraw.Draw(img)
        d.ellipse([2, 2, 62, 62], fill=(180, 180, 200, 230))
        d.ellipse([18, 18, 46, 46], fill=(10, 10, 15, 255))
        return img


_window: webview.Window = None


def _tray_loop():
    """pystray — ayrı thread'de çalışır."""
    def on_show(icon, item):
        if _window:
            _window.show()

    def on_hide(icon, item):
        if _window:
            _window.hide()

    def on_quit(icon, item):
        icon.stop()
        if _window:
            _window.destroy()

    menu = pystray.Menu(
        pystray.MenuItem('Göster',  on_show),
        pystray.MenuItem('Gizle',   on_hide),
        pystray.MenuItem('Kapat',   on_quit),
    )
    tray = pystray.Icon('Kuroshin', _make_icon(), 'Kuroshin', menu)
    tray.run()


def main():
    global _window

    # ── Argüman ──
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mode', default=None)
    args, _ = parser.parse_known_args()

    settings = _load_settings()
    if args.mode:
        settings['mode'] = args.mode

    api_obj  = KuroshinAPI(settings, SETTINGS_PATH)
    mode_mgr = ModeManager(settings)

    # Tray → arka plan thread
    threading.Thread(target=_tray_loop, daemon=True).start()

    # Mod başlat
    mode_mgr.start(settings.get('mode', 'lite'))

    # Pencere boyutu (panel kapalı: sadece orb 92×92)
    panel_open = settings.get('panel_open', False)
    win_w = 370 if panel_open else 92
    win_h = 580 if panel_open else 92

    # index.html yolu (file:/// protokolü, ters-eğik çizgi olmadan)
    index_url = 'file:///' + WEB_DIR.replace('\\', '/') + '/index.html'

    _window = webview.create_window(
        title='Kuroshin',
        url=index_url,
        js_api=api_obj,
        width=win_w,
        height=win_h,
        x=settings.get('orb_x', 1812),
        y=settings.get('orb_y', 972),
        frameless=True,
        transparent=True,
        on_top=True,
        easy_drag=False,
        min_size=(64, 64),
        background_color='#00000000',
    )

    api_obj.set_window(_window)

    # pywebview main thread zorunlu
    webview.start(debug=False)


if __name__ == '__main__':
    main()
