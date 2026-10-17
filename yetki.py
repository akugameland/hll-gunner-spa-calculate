"""Öndeki pencere (oyun) yönetici olarak mı çalışıyor?

Windows (UIPI): yönetici olarak çalışan bir pencere öndeyken, yönetici olmayan programın klavye kancası
o pencereye giden tuşları hiç görmez. Oyun yönetici olarak açıldıysa bas-konuş çalışmaz; program da
yönetici olarak açılmalıdır. Bilinemezse (erişim reddi) None döner ve uyarı gösterilmez.
"""
import ctypes
from ctypes import wintypes

_u32 = ctypes.windll.user32
_k32 = ctypes.windll.kernel32
_adv = ctypes.windll.advapi32
_k32.OpenProcess.restype = wintypes.HANDLE
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TOKEN_ELEVATION = 20


def biz_yonetici() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _yonetici_mi(pid: int) -> bool | None:
    islem = _k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not islem:
        return None
    try:
        jeton = wintypes.HANDLE()
        if not _adv.OpenProcessToken(islem, TOKEN_QUERY, ctypes.byref(jeton)):
            return None
        try:
            deger, boyut = wintypes.DWORD(), wintypes.DWORD()
            if not _adv.GetTokenInformation(jeton, TOKEN_ELEVATION, ctypes.byref(deger),
                                            ctypes.sizeof(deger), ctypes.byref(boyut)):
                return None
            return bool(deger.value)
        finally:
            _k32.CloseHandle(jeton)
    finally:
        _k32.CloseHandle(islem)


def on_pencere_yonetici() -> bool | None:
    hwnd = _u32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return _yonetici_mi(pid.value) if pid.value else None


def tuslar_engelli_mi() -> bool:
    """Öndeki pencere yönetici, biz değilsek True (tuşlar bize gelmez)."""
    return not biz_yonetici() and on_pencere_yonetici() is True
