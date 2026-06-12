import json
import os
import subprocess
import urllib.request

from PyQt6.QtCore import QObject, pyqtSlot


class KuroshinAPI(QObject):
    def __init__(self, settings: dict, settings_path: str):
        super().__init__()
        self._s    = settings
        self._path = settings_path
        self._win  = None

    def set_window(self, win):
        self._win = win

    # ── Pencere kontrolu ──────────────────────────────
    @pyqtSlot(int, int)
    def move_window(self, x, y):
        if self._win:
            self._win.move(int(x), int(y))

    @pyqtSlot(bool)
    def toggle_panel(self, open_state):
        if self._win:
            if open_state:
                self._win.resize(370, 580)
            else:
                self._win.resize(92, 92)
        self._s['panel_open'] = bool(open_state)
        self._save()

    @pyqtSlot(int, int, str)
    def save_position(self, x, y, corner):
        self._s['orb_x']      = int(x)
        self._s['orb_y']      = int(y)
        self._s['orb_corner'] = str(corner)
        self._save()

    @pyqtSlot()
    def quit(self):
        if self._win:
            self._win.close()

    # ── Ayarlar ──────────────────────────────────────
    @pyqtSlot(result='QVariantMap')
    def get_settings(self):
        return dict(self._s)

    # ── Status LED ───────────────────────────────────
    @pyqtSlot(result='QVariantMap')
    def get_status(self):
        result = {}
        for key, port, path in [('ch', 9005, '/health'),
                                 ('lm', 8080, '/health'),
                                 ('wk', 9002, '/health')]:
            try:
                r = urllib.request.urlopen(
                    f'http://localhost:{port}{path}', timeout=0.5
                )
                result[key] = r.status == 200
            except Exception:
                result[key] = False
        return result

    # ── Mesaj ────────────────────────────────────────
    @pyqtSlot(str, result=str)
    def send_message(self, text: str):
        return "[FAZ-2] Chancellor baglantisi henuz kurulmadi."

    # ── Sistem butonlari ─────────────────────────────
    @pyqtSlot()
    def ram_purge(self):
        subprocess.Popen(
            ['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
             'sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true'],
            shell=False, creationflags=0x08000000
        )

    @pyqtSlot()
    def llm_toggle(self):
        pass

    @pyqtSlot()
    def chancellor_restart(self):
        subprocess.Popen(
            ['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
             'bash /mnt/c/Kuroshin/scripts/restart_chancellor.sh'],
            shell=False, creationflags=0x08000000
        )

    @pyqtSlot()
    def show_alarms(self):
        pass

    # ── Ic yardimci ──────────────────────────────────
    def _save(self):
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._s, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
