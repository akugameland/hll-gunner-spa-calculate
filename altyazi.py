"""Ekranın altında film altyazısı gibi duran, her zaman en önde, tıklamaları geçiren katman.

CanYouSpeak'in (github.com/akugameland/canyouspeak, altyazi.py) sadeleştirilmiş hâli; pencere hileleri ve dersler oradan:
- Tk, -alpha / -transparentcolor / -topmost her ayarlandığında WS_EX_TRANSPARENT'ı siliyor; düzenli yeniden uygulanır.
- Oyun penceresi de en-önde olursa HWND_TOPMOST yetmeyebiliyor; NOTOPMOST -> TOPMOST sıçratması yapılır.
- Tam ekran (exclusive fullscreen) oyunda hiçbir pencere oyunun üstüne çıkamaz: oyun "kenarlıksız pencere" olmalı.
"""
import ctypes
import os
import tkinter as tk
from ctypes import wintypes

ANAHTAR_RENK = "#010203"
USTTE_TUT_MS = 400

_u32 = ctypes.windll.user32
_u32.GetWindow.restype = wintypes.HWND
_u32.GetWindow.argtypes = (wintypes.HWND, wintypes.UINT)
GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE, WS_EX_TOPMOST = \
    0x80000, 0x20, 0x80, 0x08000000, 0x8
TIKLAMA_GECIR = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
GW_HWNDPREV = 3
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
_KENDI_PID = os.getpid()


def _tiklama_gecir(hwnd: int):
    stil = _u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if stil & TIKLAMA_GECIR != TIKLAMA_GECIR:
        _u32.SetWindowLongW(hwnd, GWL_EXSTYLE, stil | TIKLAMA_GECIR)


def _en_one(hwnd: int, nereye=HWND_TOPMOST):
    _u32.SetWindowPos(hwnd, nereye, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def _ustumuzde_pencere_var(hwnd: int) -> bool:
    """Altyazıyı örten, başka bir programa ait en-önde pencere var mı?"""
    biz = wintypes.RECT()
    _u32.GetWindowRect(hwnd, ctypes.byref(biz))
    h = _u32.GetWindow(hwnd, GW_HWNDPREV)
    for _ in range(500):
        if not h:
            return False
        o, pid = wintypes.RECT(), wintypes.DWORD()
        _u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if (pid.value != _KENDI_PID and _u32.IsWindowVisible(h)
                and _u32.GetWindowLongW(h, GWL_EXSTYLE) & WS_EX_TOPMOST
                and _u32.GetWindowRect(h, ctypes.byref(o))
                and o.left < biz.right and biz.left < o.right and o.top < biz.bottom and biz.top < o.bottom):
            return True
        h = _u32.GetWindow(h, GW_HWNDPREV)
    return False


class Altyazi:
    """satirlar: [(metin, renk, boyut_orani, kalin)], yukarıdan aşağı. boyut_orani temel boyuta göre."""

    def __init__(self, kok: tk.Tk, boyut: int = 30, alt_bosluk: int = 18, yazi_tipi: str = "Segoe UI"):
        self.kok = kok
        self.p = tk.Toplevel(kok)
        self.p.overrideredirect(True)
        self.p.configure(bg=ANAHTAR_RENK)
        self.p.attributes("-topmost", True)
        self.p.attributes("-transparentcolor", ANAHTAR_RENK)
        self.c = tk.Canvas(self.p, bg=ANAHTAR_RENK, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.p.update_idletasks()
        self.hwnd = _u32.GetParent(self.p.winfo_id())
        self.yazi_tipi = yazi_tipi
        self.satirlar: list = []
        self.ayarla(boyut, alt_bosluk)
        self._ustte_tut()

    def ayarla(self, boyut: int, alt_bosluk: int, monitor: dict | None = None):
        """monitor: mss biçiminde {'left','top','width','height'}; verilmezse ana ekran."""
        self.boyut, self.alt_bosluk = boyut, alt_bosluk
        if monitor:
            ml, mt, mg, my = monitor["left"], monitor["top"], monitor["width"], monitor["height"]
        else:
            ml, mt, mg, my = 0, 0, self.p.winfo_screenwidth(), self.p.winfo_screenheight()
        self.gen, self.yuk = int(mg * 0.6), int(my * 0.4)
        x = ml + (mg - self.gen) // 2
        y = mt + my - self.yuk - int(my * alt_bosluk / 100)
        self.p.geometry(f"{self.gen}x{self.yuk}+{x}+{y}")
        self.c.configure(width=self.gen, height=self.yuk)
        self.p.update_idletasks()
        _tiklama_gecir(self.hwnd)
        self._ciz()

    def _ustte_tut(self):
        try:
            _tiklama_gecir(self.hwnd)
            _en_one(self.hwnd)
            if _ustumuzde_pencere_var(self.hwnd):
                _en_one(self.hwnd, HWND_NOTOPMOST)
                _en_one(self.hwnd)
        finally:
            self.p.after(USTTE_TUT_MS, self._ustte_tut)

    def yaz(self, satirlar: list):
        if satirlar != self.satirlar:          # aynıysa yeniden çizme (titreme olmasın)
            self.satirlar = satirlar
            self._ciz()

    def _ciz(self):
        self.c.delete("all")
        y = self.yuk - 4
        x = self.gen // 2
        for metin, renk, oran, kalin in reversed(self.satirlar):
            if not metin:
                continue
            yazi_tipi = (self.yazi_tipi, max(9, int(self.boyut * oran)), "bold" if kalin else "normal")
            k = 2 if oran >= 0.8 else 1
            for dx in (-k, 0, k):
                for dy in (-k, 0, k):
                    if dx or dy:
                        self.c.create_text(x + dx, y + dy, text=metin, fill="#000000", font=yazi_tipi,
                                           width=self.gen - 20, justify="center", anchor="s")
            kimlik = self.c.create_text(x, y, text=metin, fill=renk, font=yazi_tipi,
                                        width=self.gen - 20, justify="center", anchor="s")
            y = self.c.bbox(kimlik)[1] - 2
