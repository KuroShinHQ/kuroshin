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
            lm2  = ex.submit(chk, 8082)   # L2 = Mod-2 Gemma 3 4B
            wk   = ex.submit(chk, 9002)
            return {'ch': ch.result(), 'lm1': lm1.result(), 'lm2': lm2.result(), 'wk': wk.result()}

    # ── Mesaj ────────────────────────────────────────
    @pyqtSlot(str)
    def send_message(self, text: str):
        import threading
        threading.Thread(target=self._do_send_message, args=(text,), daemon=True).start()

    def _do_send_message(self, text: str):
        import re
        from pathlib import Path as _Path

        PERSONA_PATH = _Path(r"C:\Kuroshin\soul\persona.json")

        def port_open(port):
            try:
                r = urllib.request.urlopen(f'http://localhost:{port}/health', timeout=1)
                return r.status == 200
            except Exception:
                return False

        def strip_think(t):
            return re.sub(r'<think>.*?</think>', '', t, flags=re.DOTALL).strip()

        def build_system_prompt():
            try:
                p = json.loads(PERSONA_PATH.read_text(encoding='utf-8'))
                k = p.get('kimlik', {})
                return (
                    f"You are Kuroshin, a sharp AI assistant. "
                    f"Your lord is {k.get('lordum','kuroshin_user')}. "
                    f"Always start your reply with '⚔️ Lordum,' and answer in Turkish. Be brief."
                )
            except Exception:
                return "You are Kuroshin. Always start with '⚔️ Lordum,' and reply in Turkish briefly."

        def push(msg):
            if self._win:
                self._win.runJS.emit(
                    f"window.__removePending?.();"
                    f"ChatManager?.addMessage({json.dumps(msg)}, 'bot', true);"
                    "window.setOrbState?.('IDLE');"
                )

        def show_pending():
            if self._win:
                self._win.runJS.emit("window.__addPending?.();")

        if port_open(8082):
            show_pending()
            try:
                data = json.dumps({
                    'model': 'local',
                    'messages': [
                        {'role': 'system', 'content': build_system_prompt()},
                        {'role': 'user',   'content': text}
                    ],
                    'stream': False,
                    'max_tokens': 256,
                    'temperature': 1.0,
                    'top_p': 0.95,
                    'top_k': 64,
                    'min_p': 0.0,
                }).encode()
                req = urllib.request.Request(
                    'http://localhost:8082/v1/chat/completions',
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                resp = urllib.request.urlopen(req, timeout=90)
                body = json.loads(resp.read().decode())
                raw  = body['choices'][0]['message']['content']
                push(strip_think(raw) or '(boş yanıt)')
            except Exception as e:
                push(f'⚠️ Qwen3-1.7B hata: {type(e).__name__}')

        elif port_open(9005):
            show_pending()
            try:
                data = json.dumps({'text': text, 'source': 'floating_ui'}).encode()
                req = urllib.request.Request(
                    'http://localhost:9005/message',
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                resp = urllib.request.urlopen(req, timeout=15)
                body = json.loads(resp.read().decode())
                reply = body.get('reply', '')
                if reply:
                    push(reply)
                else:
                    if self._win:
                        self._win.runJS.emit(
                            "window.__removePending?.();window.setOrbState?.('IDLE');"
                        )
            except Exception as e:
                push(f'⚠️ CH hata: {type(e).__name__}')

        else:
            push('⚠️ LLM yok — panelden LLM butonuna bas')

    # ── Sistem butonlari ─────────────────────────────
    @pyqtSlot()
    def ram_purge(self):
        import threading
        threading.Thread(target=self._do_ram_purge, daemon=True).start()

    def _do_ram_purge(self):
        import ctypes, ctypes.wintypes, time
        import psutil as _ps

        kernel32 = ctypes.windll.kernel32
        advapi32 = ctypes.windll.advapi32
        ntdll    = ctypes.windll.ntdll

        mem_before = _ps.virtual_memory().available

        # NtSetSystemInformation için SeProfileSingleProcessPrivilege gerekir
        class _LUID(ctypes.Structure):
            _fields_ = [('LowPart', ctypes.c_ulong), ('HighPart', ctypes.c_long)]

        class _LUID_ATTR(ctypes.Structure):
            _fields_ = [('Luid', _LUID), ('Attributes', ctypes.c_ulong)]

        class _TOKEN_PRIVS(ctypes.Structure):
            _fields_ = [('PrivilegeCount', ctypes.c_ulong),
                        ('Privileges', _LUID_ATTR * 1)]

        def _enable_priv(name):
            TOKEN_ADJUST_PRIVILEGES = 0x0020
            TOKEN_QUERY             = 0x0008
            SE_PRIVILEGE_ENABLED    = 0x00000002
            h = ctypes.wintypes.HANDLE()
            if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                             TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                             ctypes.byref(h)):
                return
            luid = _LUID()
            if advapi32.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
                tp = _TOKEN_PRIVS()
                tp.PrivilegeCount = 1
                tp.Privileges[0].Luid = luid
                tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
                advapi32.AdjustTokenPrivileges(h, False, ctypes.byref(tp),
                                               ctypes.sizeof(tp), None, None)
            kernel32.CloseHandle(h)

        _enable_priv("SeProfileSingleProcessPrivilege")
        _enable_priv("SeLockMemoryPrivilege")

        SystemMemoryListInformation = 80
        MemoryEmptyWorkingSet       = 2   # tüm process working setleri boşalt
        MemoryFlushModifiedList     = 3   # modified page list temizle
        MemoryPurgeStandbyList      = 4   # standby list temizle

        # İlk çağrının return değeri: 0=OK, 0xC0000022=ACCESS_DENIED (admin yok)
        ntdll.NtSetSystemInformation.restype = ctypes.c_long
        first_cmd = ctypes.c_uint32(MemoryEmptyWorkingSet)
        status = ntdll.NtSetSystemInformation(SystemMemoryListInformation,
                                              ctypes.byref(first_cmd), 4)

        ACCESS_DENIED = -1073741790  # 0xC0000022 signed

        if status == ACCESS_DENIED or status != 0:
            # UAC elevation ile helper'ı admin olarak çalıştır
            import sys as _sys
            HELPER = r"C:\Kuroshin\kuroshin_floating_ui\ram_purge_helper.py"
            RESULT_FILE = os.path.join(
                os.environ.get('TEMP', r'C:\Windows\Temp'),
                'kuroshin_ram_purge_result.txt'
            )
            try: os.remove(RESULT_FILE)
            except: pass

            if getattr(_sys, 'frozen', False):
                r2 = subprocess.run(['where', 'pythonw.exe'], capture_output=True,
                                    text=True, creationflags=0x08000000)
                pyexe = r2.stdout.strip().split('\n')[0].strip() if r2.returncode == 0 else 'pythonw.exe'
            else:
                pyexe = _sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(pyexe):
                    pyexe = _sys.executable

            ret = ctypes.windll.shell32.ShellExecuteW(
                None, 'runas', pyexe, HELPER, None, 0
            )
            if ret > 32:  # ShellExecuteW başarısı: >32 = OK
                for _ in range(20):
                    time.sleep(0.5)
                    if os.path.exists(RESULT_FILE):
                        break
                mem_after = _ps.virtual_memory()
                freed_mb  = (mem_after.available - mem_before) // (1024 * 1024)
                free_gb   = round(mem_after.available / 1073741824, 1)
                msg = f"+{freed_mb} MB · {free_gb} GB serbest (admin)"
            else:
                free_gb = round(_ps.virtual_memory().available / 1073741824, 1)
                msg = f"⛔ UAC iptal · {free_gb} GB serbest"
        else:
            # Admin var → kalan iki komutu da çalıştır
            for cmd_val in (MemoryFlushModifiedList, MemoryPurgeStandbyList):
                cmd = ctypes.c_uint32(cmd_val)
                ntdll.NtSetSystemInformation(SystemMemoryListInformation,
                                             ctypes.byref(cmd), 4)
            time.sleep(0.5)
            mem_after = _ps.virtual_memory()
            freed_mb  = (mem_after.available - mem_before) // (1024 * 1024)
            free_gb   = round(mem_after.available / 1073741824, 1)
            msg = f"+{freed_mb} MB boşaldı · {free_gb} GB serbest" if freed_mb > 30 \
                  else f"RAM zaten temiz · {free_gb} GB serbest"

        if self._win:
            self._win.runJS.emit(
                f"ChatManager?.addMessage('🧹 {msg}', 'bot', true);"
            )

    @pyqtSlot(result='QVariantMap')
    def get_hw_stats(self):
        import psutil as _ps, subprocess as _sp
        cpu_pct = _ps.cpu_percent(interval=None)
        vm = _ps.virtual_memory()
        gpu_pct, gpu_temp, cpu_temp = -1, -1, -1
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
        return {
            'cpu_pct':      round(cpu_pct, 1),
            'ram_used_gb':  round(vm.used   / 1073741824, 1),
            'ram_total_gb': round(vm.total  / 1073741824, 1),
            'ram_pct':      round(vm.percent, 1),
            'gpu_pct':      gpu_pct,
            'gpu_temp':     gpu_temp,
            'cpu_temp':     cpu_temp,
        }

    @pyqtSlot()
    def llm_toggle(self):
        import threading
        threading.Thread(target=self._do_llm_toggle, daemon=True).start()

    def _do_llm_toggle(self):
        NWIN = 0x08000000  # CREATE_NO_WINDOW

        running = False
        try:
            r = urllib.request.urlopen('http://localhost:8082/health', timeout=1)
            running = (r.status == 200)
        except Exception:
            pass

        if running:
            subprocess.Popen(
                ['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
                 "pkill -9 -f 'llama-server.*8082' 2>/dev/null; sleep 1"],
                creationflags=NWIN
            )
            msg = '⬛ Mod-2 (Gemma 3 4B) durduruldu'
        else:
            subprocess.Popen(
                ['wsl', '-d', 'Ubuntu-22.04', '--', 'bash',
                 '/mnt/c/Kuroshin/scripts/start_gemma3_l2.sh'],
                creationflags=NWIN
            )
            msg = '🔄 Mod-2 başlatılıyor... (Gemma 3 4B · port 8082 · hazır olunca bildirim)'
            import threading as _thr
            _thr.Thread(target=self._wait_lm2_ready, daemon=True).start()

        if self._win:
            self._win.runJS.emit(f"ChatManager?.addMessage('{msg}', 'bot', true);")

    def _wait_lm2_ready(self):
        import time
        for _ in range(30):
            time.sleep(3)
            try:
                r = urllib.request.urlopen('http://localhost:8082/health', timeout=1)
                if r.status == 200:
                    if self._win:
                        self._win.runJS.emit(
                            "ChatManager?.addMessage('✅ Mod-2 hazır — Gemma 3 4B aktif', 'bot', true);"
                        )
                    return
            except Exception:
                pass
        if self._win:
            self._win.runJS.emit(
                "ChatManager?.addMessage('⚠️ Mod-2 başlamadı (90s timeout)', 'bot', true);"
            )

    @pyqtSlot()
    def chancellor_restart(self):
        import threading
        threading.Thread(target=self._do_chancellor_restart, daemon=True).start()

    def _do_chancellor_restart(self):
        import time
        subprocess.Popen(
            ['wsl', '-d', 'Ubuntu-22.04', '--', 'bash', '-c',
             'bash /mnt/c/Kuroshin/scripts/restart_chancellor.sh'],
            shell=False, creationflags=0x08000000
        )
        time.sleep(30)  # Chancellor ~26sn başlıyor (restart_chancellor.sh max 26s bekler)
        try:
            r = urllib.request.urlopen('http://localhost:9005/health', timeout=3)
            ok = r.status == 200
        except Exception:
            ok = False
        msg = '✅ Chancellor yeniden başlatıldı' if ok else '⚠️ Restart gönderildi (CH bağlantısı bekleniyor...)'
        if self._win:
            self._win.runJS.emit(f"ChatManager?.addMessage('{msg}', 'bot', true);")

    @pyqtSlot()
    def show_alarms(self):
        import threading
        threading.Thread(target=self._do_show_alarms, daemon=True).start()

    def _do_show_alarms(self):
        import re
        config_path = r"C:\Kuroshin\KuroRecon\alarm_config.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            parts = re.split(r'\n  - name:', content)
            enabled = []
            for part in parts[1:]:
                if 'enabled:     true' not in part and 'enabled: true' not in part:
                    continue
                name_m  = re.search(r'^(.+?)$', part.strip(), re.MULTILINE)
                below_m = re.search(r'below_price:\s*(\d+)', part)
                drop_m  = re.search(r'drop_percent:\s*(\d+)', part)
                name = name_m.group(1).strip().strip('"') if name_m else '?'
                if below_m:
                    enabled.append(f'· {name} < {int(below_m.group(1)):,}₺')
                elif drop_m:
                    enabled.append(f'· {name} %{drop_m.group(1)} düşüş')
                else:
                    enabled.append(f'· {name}')
            if not enabled:
                msg = '🔔 Aktif alarm yok<br>alarm_config.yaml → enabled: true yap'
            else:
                msg = f'🔔 {len(enabled)} aktif:<br>' + '<br>'.join(enabled)
        except FileNotFoundError:
            msg = '⚠️ alarm_config.yaml bulunamadı'
        except Exception as e:
            msg = f'⚠️ Alarm hatası: {e}'
        if self._win:
            self._win.runJS.emit(
                f"ChatManager?.addMessage({json.dumps(msg)}, 'bot', true);"
            )

    # ── Ic yardimci ──────────────────────────────────
    def _save(self):
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._s, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
