import os
import subprocess


class ModeManager:
    LITE       = 'lite'
    FULL_POWER = 'full_power'

    def __init__(self, settings: dict):
        self._s       = settings
        self._current = None

    def start(self, mode: str):
        self._current = mode
        if mode == self.FULL_POWER:
            self._start_full_power()
        # LITE: sadece UI + bridge çalışır, WSL/llama/chancellor başlatılmaz

    def _start_full_power(self):
        """bat [1] simülasyonu — Kuroshin tam sistemi başlat."""
        bat = r'C:\Kuroshin\Kuroshin.bat'
        if os.path.exists(bat):
            subprocess.Popen(
                ['cmd', '/c', 'start', '', bat],
                shell=False,
                creationflags=0x00000008,  # DETACHED_PROCESS
            )

    def stop_all(self):
        pass  # FAZ-3'te dolar

    @property
    def current(self) -> str:
        return self._current
