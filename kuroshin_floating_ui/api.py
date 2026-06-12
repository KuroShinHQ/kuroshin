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
        if not self._win:
            return
        import ctypes as _ct
        sw = _ct.windll.user32.GetSystemMetrics(0)
        sh = _ct.windll.user32.GetSystemMetrics(1)
        OW = 92; PW, PH = 370, 580

        if open_state:
            ox, oy = self._win.x(), self._win.y()
            # Orb top-left screen pos (CSS: bottom:16, right:16 in 92×92 window)
            orb_sx = ox + OW - 16 - 64   # ox+12
            orb_sy = oy + OW - 16 - 64   # oy+12
            on_right  = (orb_sx + 32) > sw // 2
            on_bottom = (orb_sy + 32) > sh // 2

            if on_right and on_bottom:
                direction = 'bottom-right'
                orb_in = (PW - 16 - 64, PH - 16 - 64)  # (290, 500)
            elif not on_right and on_bottom:
                direction = 'bottom-left'
                orb_in = (16, PH - 16 - 64)             # (16, 500)
            elif on_right:
                direction = 'top-right'
                orb_in = (PW - 16 - 64, 16)             # (290, 16)
            else:
                direction = 'top-left'
                orb_in = (16, 16)

            new_x = max(0, min(orb_sx - orb_in[0], sw - PW))
            new_y = max(0, min(orb_sy - orb_in[1], sh - PH))
            self._panel_dir = direction
            self._win.setGeometry(new_x, new_y, PW, PH)
            self._win.web.page().runJavaScript(
                f"document.getElementById('ui-root').dataset.dir='{direction}';"
            )
        else:
            direction = getattr(self, '_panel_dir', 'bottom-right')
            px, py = self._win.x(), self._win.y()
            if direction == 'bottom-right': orb_in = (PW-16-64, PH-16-64)
            elif direction == 'bottom-left': orb_in = (16, PH-16-64)
            elif direction == 'top-right':   orb_in = (PW-16-64, 16)
            else:                            orb_in = (16, 16)
            orb_sx = px + orb_in[0]
            orb_sy = py + orb_in[1]
            new_x = max(0, min(orb_sx - 12, sw - OW))
            new_y = max(0, min(orb_sy - 12, sh - OW))
            self._s['orb_x'] = new_x
            self._s['orb_y'] = new_y
            self._win.setGeometry(new_x, new_y, OW, OW)

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
        import concurrent.futures
        def chk(port):
            try:
                r = urllib.request.urlopen(f'http://localhost:{port}/health', timeout=0.5)
                return r.status == 200
            except Exception:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            ch   = ex.submit(chk, 9005)
            lm1  = ex.submit(chk, 8080)   # L1 = Huihui-35B
            lm2  = ex.submit(chk, 8082)   # L2 = Mod-2 Qwen3-1.7B
            wk   = ex.submit(chk, 9002)
            return {'ch': ch.result(), 'lm1': lm1.result(), 'lm2': lm2.result(), 'wk': wk.result()}

    # ── Mesaj ────────────────────────────────────────
    @pyqtSlot(str, result=str)
    def send_message(self, text: str):
        return "[FAZ-2] Chancellor baglantisi henuz kurulmadi."

    # ── Sistem butonlari ─────────────────────────────
    @pyqtSlot()
    def ram_purge(self):
        import threading
        threading.Thread(target=self._do_ram_purge, daemon=True).start()

    def _do_ram_purge(self):
        import ctypes
        import ctypes.wintypes
        kernel32 = ctypes.windll.kernel32
        psapi    = ctypes.windll.psapi

        pids  = (ctypes.c_ulong * 2048)()
        cb    = ctypes.c_ulong()
        psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(cb))
        count = cb.value // ctypes.sizeof(ctypes.c_ulong)

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        PROCESS_SET_QUOTA                 = 0x0100
        PROCESS_VM_OPERATION              = 0x0008
        access = PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SET_QUOTA | PROCESS_VM_OPERATION

        emptied = 0
        for pid in list(pids)[:count]:
            if not pid:
                continue
            h = kernel32.OpenProcess(access, False, pid)
            if h:
                psapi.EmptyWorkingSet(h)
                kernel32.CloseHandle(h)
                emptied += 1

        if self._win:
            self._win.runJS.emit(
                f"ChatManager?.addMessage('🧹 RAM temizlendi — {emptied} process working set boşaltıldı', 'bot', true);"
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
