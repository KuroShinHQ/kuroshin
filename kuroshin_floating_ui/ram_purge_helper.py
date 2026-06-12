"""
RAM Purge Helper — SYSTEM yetkisiyle schtasks tarafından çalıştırılır.
NtSetSystemInformation ile standby list + working sets + modified list temizler.
Sonuç: %TEMP%\kuroshin_ram_purge_result.txt
"""
import ctypes, ctypes.wintypes, time, os

ntdll    = ctypes.windll.ntdll
kernel32 = ctypes.windll.kernel32
advapi32 = ctypes.windll.advapi32

def _enable_priv(name):
    TOKEN_ADJUST_PRIVILEGES = 0x0020
    TOKEN_QUERY             = 0x0008
    SE_PRIVILEGE_ENABLED    = 0x00000002

    class _LUID(ctypes.Structure):
        _fields_ = [('LowPart', ctypes.c_ulong), ('HighPart', ctypes.c_long)]

    class _LUID_ATTR(ctypes.Structure):
        _fields_ = [('Luid', _LUID), ('Attributes', ctypes.c_ulong)]

    class _TP(ctypes.Structure):
        _fields_ = [('PrivilegeCount', ctypes.c_ulong), ('Privileges', _LUID_ATTR * 1)]

    h = ctypes.wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(h)):
        return
    luid = _LUID()
    if advapi32.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
        tp = _TP()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        advapi32.AdjustTokenPrivileges(h, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
    kernel32.CloseHandle(h)

_enable_priv("SeProfileSingleProcessPrivilege")
_enable_priv("SeLockMemoryPrivilege")

SystemMemoryListInformation = 80
ntdll.NtSetSystemInformation.restype = ctypes.c_long

results = []
for cmd_val in (2, 3, 4):  # EmptyWorkingSet, FlushModified, PurgeStandby
    cmd = ctypes.c_uint32(cmd_val)
    r = ntdll.NtSetSystemInformation(SystemMemoryListInformation, ctypes.byref(cmd), 4)
    results.append(f"cmd{cmd_val}={r:#010x}")

time.sleep(0.3)

result_file = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'),
                           'kuroshin_ram_purge_result.txt')
with open(result_file, 'w') as f:
    f.write('\n'.join(results))
