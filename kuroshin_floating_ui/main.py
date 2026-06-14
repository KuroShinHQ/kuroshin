"""
Kuroshin Floating UI — PyQt6 + QWebEngineView
Gercek seffaflik: WA_TranslucentBackground + transparent WebEngine background
"""
import sys
import os
import json
import threading
import argparse
import ctypes
import ctypes.wintypes

if getattr(sys, 'frozen', False):
    _RES  = sys._MEIPASS
    _DATA = os.path.dirname(sys.executable)
else:
    _RES  = os.path.dirname(os.path.abspath(__file__))
    _DATA = _RES
SETTINGS_PATH = os.path.join(_DATA, 'settings.json')
WEB_DIR       = os.path.join(_RES,  'web')
ICON_PATH     = os.path.join(_DATA, 'icon.ico')

# Tek instance kilidi
_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, True, 'KuroshinFloatingUI_SingleInstance')
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

sys.path.insert(0, _RES)

import pystray
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QIcon

from api    import KuroshinAPI
from modes  import ModeManager
from bridge import start as bridge_start


def _load_settings():
    try:
        with open(SETTINGS_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _screen_size():
    ctypes.windll.user32.SetProcessDPIAware()
    return (ctypes.windll.user32.GetSystemMetrics(0),
            ctypes.windll.user32.GetSystemMetrics(1))


def _hide_from_taskbar():
    import time
    time.sleep(0.8)
    hwnd = ctypes.windll.user32.FindWindowW(None, 'Kuroshin')
    if not hwnd:
        return
    GWL_EXSTYLE      = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW  = 0x00040000
    old = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                        (old | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)


class OrbWindow(QMainWindow):
    runJS = pyqtSignal(str)

    def __init__(self, api_obj, settings):
        super().__init__()
        self._api = api_obj

        self.setWindowTitle('Kuroshin')
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # Boyut + pozisyon
        sw, sh = _screen_size()
        panel_open = settings.get('panel_open', False)
        w = 370 if panel_open else 92
        h = 580 if panel_open else 92
        x = int(settings.get('orb_x', sw - w - 16))
        y = int(settings.get('orb_y', sh - h - 16))
        self.setGeometry(x, y, w, h)

        # WebEngine — transparan
        self.web = QWebEngineView()
        self.web.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.web.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # QWebChannel — JS <-> Python koprusu
        self.channel = QWebChannel()
        self.channel.registerObject('api', api_obj)
        self.web.page().setWebChannel(self.channel)

        # Mikrofon izni — ses reaktif orb için otomatik onayla
        self.web.page().featurePermissionRequested.connect(self._grant_permission)

        self.setCentralWidget(self.web)
        self.web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self.runJS.connect(lambda js: self.web.page().runJavaScript(js))

        index_path = os.path.join(WEB_DIR, 'index.html')
        self.web.load(QUrl.fromLocalFile(index_path))

        api_obj.set_window(self)

    def _grant_permission(self, url, feature):
        from PyQt6.QtWebEngineCore import QWebEnginePage
        self.web.page().setFeaturePermission(
            url, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
        )


def _make_tray_icon():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([2, 2, 62, 62],   fill=(180, 180, 200, 230))
    d.ellipse([18, 18, 46, 46], fill=(10,  10,  15,  255))
    return img


def _ensure_icon():
    """icon.ico yoksa tray ikonundan üret — Görev Yöneticisi ikonu."""
    if os.path.exists(ICON_PATH):
        return ICON_PATH
    try:
        os.makedirs(os.path.dirname(ICON_PATH) or '.', exist_ok=True)
        img = _make_tray_icon().resize((32, 32), Image.LANCZOS)
        img.save(ICON_PATH, format='ICO', sizes=[(32, 32), (16, 16)])
        return ICON_PATH
    except Exception:
        return None


def _tray_loop(qt_app, window):
    def on_show(icon, item):
        window.show()

    def on_hide(icon, item):
        window.hide()

    def on_quit(icon, item):
        icon.stop()
        qt_app.quit()

    icon = pystray.Icon(
        'Kuroshin',
        _make_tray_icon(),
        menu=pystray.Menu(
            pystray.MenuItem('Goster',  on_show),
            pystray.MenuItem('Gizle',   on_hide),
            pystray.MenuItem('Cikis',   on_quit),
        )
    )
    icon.run()


def _setup_orb_mouse_hotkey(api_obj):
    """Ctrl+Alt+U/U-umlaut → orb mouse konumuna isinlanir, HWND_TOPMOST."""
    try:
        import keyboard as _kb

        def _jump_to_mouse():
            pt = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            mx, my = int(pt.x), int(pt.y)
            nx = max(0, mx - 46)
            ny = max(0, my - 46)

            hwnd = ctypes.windll.user32.FindWindowW(None, 'Kuroshin')
            if hwnd:
                HWND_TOPMOST   = -1
                SWP_NOSIZE     = 0x0001
                SWP_SHOWWINDOW = 0x0040
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, nx, ny, 0, 0, SWP_NOSIZE | SWP_SHOWWINDOW
                )
            api_obj.save_position(nx, ny, 'free')

        try:
            _kb.add_hotkey('ctrl+alt+0', _jump_to_mouse, suppress=True)
        except Exception:
            pass

    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='lite')
    args = parser.parse_args()

    settings = _load_settings()

    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setApplicationName("Kuroshin")
    qt_app.setApplicationDisplayName("Kuroshin")
    ico = _ensure_icon()
    if ico:
        qt_app.setWindowIcon(QIcon(ico))

    api_obj  = KuroshinAPI(settings, SETTINGS_PATH)
    mode_mgr = ModeManager(settings)

    window = OrbWindow(api_obj, settings)
    window.show()

    bridge_start()
    threading.Thread(target=_hide_from_taskbar, daemon=True).start()
    _setup_orb_mouse_hotkey(api_obj)
    threading.Thread(target=_tray_loop, args=(qt_app, window), daemon=True).start()

    def _led_poll(win):
        import time, concurrent.futures, urllib.request as _req
        def chk(port):
            try: return _req.urlopen(f'http://localhost:{port}/health', timeout=0.5).status == 200
            except: return False
        while True:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                ch  = ex.submit(chk, 9005)
                lm1 = ex.submit(chk, 8080)   # L1 = Huihui-35B
                lm2 = ex.submit(chk, 8082)   # L2 = Mod-2 Qwen3-1.7B
                wk  = ex.submit(chk, 9002)
                s = {'ch':  ch.result(),
                     'lm1': lm1.result(),
                     'lm2': lm2.result(),
                     'wk':  wk.result()}
            win.runJS.emit(
                f"window.currentLEDStatus={json.dumps(s)};"
                f"typeof updateLEDs==='function'&&updateLEDs({json.dumps(s)})"
            )
            time.sleep(10)

    threading.Thread(target=_led_poll, args=(window,), daemon=True).start()

    def _hw_poll(win):
        import time, psutil as _ps, subprocess as _sp
        _ps.cpu_percent()   # ilk çağrı her zaman 0 döner — ısındırma
        while True:
            time.sleep(3)
            try:
                cpu_pct  = _ps.cpu_percent()
                vm       = _ps.virtual_memory()
                gpu_pct  = -1; gpu_temp = -1; cpu_temp = -1
                try:
                    r = _sp.run(
                        ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu',
                         '--format=csv,noheader,nounits'],
                        capture_output=True, text=True, timeout=2,
                        creationflags=0x08000000  # CREATE_NO_WINDOW
                    )
                    if r.returncode == 0:
                        p = r.stdout.strip().split(',')
                        gpu_pct, gpu_temp = int(p[0].strip()), int(p[1].strip())
                except Exception:
                    pass
                try:
                    t = _ps.sensors_temperatures()
                    for k in ('coretemp', 'acpitz', 'k10temp', 'it8'):
                        if k in t:
                            cpu_temp = int(t[k][0].current); break
                except Exception:
                    pass
                s = {
                    'cpu_pct':      round(cpu_pct, 1),
                    'ram_used_gb':  round(vm.used   / 1073741824, 1),
                    'ram_total_gb': round(vm.total  / 1073741824, 1),
                    'ram_pct':      round(vm.percent, 1),
                    'gpu_pct':      gpu_pct,
                    'gpu_temp':     gpu_temp,
                    'cpu_temp':     cpu_temp,
                }
                win.runJS.emit(
                    f"typeof updateHW==='function'&&updateHW({json.dumps(s)})"
                )
            except Exception:
                pass

    threading.Thread(target=_hw_poll, args=(window,), daemon=True).start()

    # Başlangıç auto-open — sayfa + pywebview init (~2s) bekle, sonra openPanel() çağır
    if settings.get('auto_open', False):
        def _startup_open(win):
            import time
            time.sleep(2.2)
            win.runJS.emit("window.openPanel?.();")
        threading.Thread(target=_startup_open, args=(window,), daemon=True).start()

    mode_mgr.start(settings.get('mode', 'lite'))

    sys.exit(qt_app.exec())


if __name__ == '__main__':
    main()

