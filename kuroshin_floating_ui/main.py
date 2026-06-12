"""
Kuroshin Floating UI — Ana giriş noktası
Başlatma: pythonw main.py [--mode lite|full_power]
"""
import sys
import os
import json
import threading
import argparse
import ctypes
import ctypes.wintypes

HERE          = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(HERE, 'settings.json')
WEB_DIR       = os.path.join(HERE, 'web')
ICON_PATH     = os.path.join(HERE, 'assets', 'icon.ico')

sys.path.insert(0, HERE)

import webview
import pystray
from PIL import Image, ImageDraw

from api    import KuroshinAPI
from modes  import ModeManager
from bridge import start as bridge_start


def _load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            'orb_x': None, 'orb_y': None,
            'orb_corner': 'bottom-right',
            'mode': 'lite', 'panel_open': False,
            'opacity': 0.92, 'theme': 'dark',
        }


def _screen_size() -> tuple[int, int]:
    """Primary ekranın fiziksel çözünürlüğünü döndür."""
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    w = user32.GetSystemMetrics(0)   # SM_CXSCREEN
    h = user32.GetSystemMetrics(1)   # SM_CYSCREEN
    return w, h


def _default_pos(win_w: int, win_h: int) -> tuple[int, int]:
    """Sağ alt köşe pozisyonunu hesapla (taskbar = ~48px)."""
    sw, sh = _screen_size()
    x = sw - win_w - 20
    y = sh - win_h - 56   # 56 = taskbar yüksekliği
    return x, y


def _hide_from_taskbar():
    """
    Pencereyi Windows taskbar'dan gizle.
    WS_EX_TOOLWINDOW → taskbar girişi yok.
    hide+show döngüsü ile değişikliği uygula.
    """
    import time
    time.sleep(1.0)          # pencere oluşana kadar bekle

    GWL_EXSTYLE      = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW  = 0x00040000
    SW_HIDE          = 0
    SW_SHOW          = 5

    pid = os.getpid()

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                     ctypes.wintypes.HWND,
                                     ctypes.wintypes.LPARAM)

    targets = []

    def _cb(hwnd, _):
        win_pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(
            hwnd, ctypes.byref(win_pid)
        )
        if win_pid.value == pid:
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new   = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new)
            targets.append(hwnd)
        return True

    ctypes.windll.user32.EnumWindows(WNDENUMPROC(_cb), 0)

    # hide → show döngüsü: Windows'un taskbar'ı yeniden değerlendirmesini sağlar
    for hwnd in targets:
        ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
        time.sleep(0.05)
        ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)


def _make_icon() -> Image.Image:
    try:
        return Image.open(ICON_PATH).convert('RGBA')
    except Exception:
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d   = ImageDraw.Draw(img)
        d.ellipse([2, 2, 62, 62],   fill=(180, 180, 200, 230))
        d.ellipse([18, 18, 46, 46], fill=(10,  10,  15,  255))
        return img


_window: webview.Window = None


def _tray_loop():
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

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mode', default=None)
    args, _ = parser.parse_known_args()

    settings = _load_settings()
    if args.mode:
        settings['mode'] = args.mode

    api_obj  = KuroshinAPI(settings, SETTINGS_PATH)
    mode_mgr = ModeManager(settings)

    # Bridge: WS :9003 hub + SSE poller (Chancellor :9005)
    bridge_start()

    # Tray → arka plan thread
    threading.Thread(target=_tray_loop, daemon=True).start()

    # Taskbar gizleme → arka plan thread (pencere açıldıktan sonra çalışır)
    threading.Thread(target=_hide_from_taskbar, daemon=True).start()

    # Mod başlat
    mode_mgr.start(settings.get('mode', 'lite'))

    # Pencere boyutu
    panel_open = settings.get('panel_open', False)
    win_w = 370 if panel_open else 92
    win_h = 580 if panel_open else 92

    # Pozisyon: settings'ten al, yoksa ekrana göre hesapla
    saved_x = settings.get('orb_x')
    saved_y = settings.get('orb_y')
    if saved_x and saved_y:
        win_x, win_y = int(saved_x), int(saved_y)
    else:
        win_x, win_y = _default_pos(win_w, win_h)

    index_url = 'file:///' + WEB_DIR.replace('\\', '/') + '/index.html'

    _window = webview.create_window(
        title='Kuroshin',
        url=index_url,
        js_api=api_obj,
        width=win_w,
        height=win_h,
        x=win_x,
        y=win_y,
        frameless=True,
        transparent=True,
        on_top=True,
        easy_drag=False,
        min_size=(64, 64),
        background_color='#000000',
    )

    api_obj.set_window(_window)

    webview.start(debug=False)


if __name__ == '__main__':
    main()
