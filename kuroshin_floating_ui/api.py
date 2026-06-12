import json
import os
import subprocess
import urllib.request


class KuroshinAPI:
    def __init__(self, settings: dict, settings_path: str):
        self._s    = settings
        self._path = settings_path
        self._win  = None

    def set_window(self, win):
        self._win = win

    # ── Pencere kontrolü ──────────────────────────────
    def move_window(self, x, y):
        if self._win:
            self._win.move(int(x), int(y))

    def toggle_panel(self, open_state):
        """Panel açılınca büyüt, kapanınca küçült."""
        if self._win:
            if open_state:
                self._win.resize(370, 580)
            else:
                self._win.resize(92, 92)
        self._s['panel_open'] = bool(open_state)
        self._save()

    def save_position(self, x, y, corner):
        self._s['orb_x']      = int(x)
        self._s['orb_y']      = int(y)
        self._s['orb_corner'] = corner
        self._save()

    def quit(self):
        if self._win:
            self._win.destroy()

    # ── Ayarlar ──────────────────────────────────────
    def get_settings(self):
        return self._s

    # ── Status LED (HTTP health check) ───────────────
    def get_status(self):
        result = {}
        checks = [
            ('ch', 9005, '/health'),
            ('lm', 8080, '/health'),
            ('wk', 9002, '/health'),
        ]
        for key, port, path in checks:
            try:
                r = urllib.request.urlopen(
                    f'http://localhost:{port}{path}', timeout=1
                )
                result[key] = r.status == 200
            except Exception:
                result[key] = False
        return result

    # ── Mesaj (FAZ-2: Chancellor bridge'e bağlanacak) ─
    def send_message(self, text: str):
        return f'[FAZ-2] Chancellor bağlantısı henüz kurulmadı. Telegram\'dan dene.'

    # ── Sistem butonları ─────────────────────────────
    def ram_purge(self):
        subprocess.Popen(
            ['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
             'sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true'],
            shell=False, creationflags=0x08000000  # CREATE_NO_WINDOW
        )

    def llm_toggle(self):
        pass  # FAZ-3'te dolar

    def chancellor_restart(self):
        subprocess.Popen(
            ['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
             'bash /mnt/c/Kuroshin/scripts/restart_chancellor.sh'],
            shell=False, creationflags=0x08000000
        )

    def show_alarms(self):
        pass  # FAZ-3'te dolar

    # ── İç yardımcı ──────────────────────────────────
    def _save(self):
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._s, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
