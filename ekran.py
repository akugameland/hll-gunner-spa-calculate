"""Oyun ekranından SPA nişangâh panelini okur (Windows'un kendi yazı tanıma motoru, internetsiz).

Sağ alttaki panel:
    PRIMARY / 105MM HOWITZER       -> tank (silah adından)
    TRAVERSE   106°
    ELEVATION  0MIL   +60MIL       -> beyaz/sarı: namlunun şu anki değeri, kırmızı: tankın eğimi

Çözünürlükten bağımsız olsun diye sabit koordinat kullanılmaz: ekranın sağ alt bölgesi okunur,
"ELEVATION" kelimesi bulunur, aynı satırda sağındaki sayılar alınır. Hangisinin kırmızı olduğuna
yazının rengine bakılarak karar verilir.
2026-10-16: 1917x1078 örnek görüntüde ölçüldü, okuma 0,02-0,05 sn.
"""
import asyncio
import re
from dataclasses import dataclass, field

import mss
import numpy as np
from PIL import Image
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import DataWriter

# Okunan bölge: ekranın sağ %32'si, alt %50'si
BOLGE_SAG = 0.32
BOLGE_ALT = 0.50

# Silah adı -> tank (site anahtarı). Sırası önemli: önce daha belirleyici olanlar.
# ❓ doğrulanacak: oyunda yalnız Sherman 105 görüldü ("105MM HOWITZER", 2026-10-16 ekran görüntüsü).
# Diğer tankların HUD'daki silah adları tahmindir; tutmazsa ayarlardan tank elle seçilir.
SILAH_ANAHTARLARI = [
    (("PETARD", "290"), "British (Churchill AVRE)"),
    (("PDR", "POUNDER", "25"), "British (Bishop SP)"),
    (("152",), "Soviet Union (KV-2)"),
    (("STUH", "150"), "Germany (Sturmpanzer IV Brummbär)"),
    (("105",), "US (Sherman M4A3 105)"),
    (("KWK", "75"), "DAK (Panzer III Ausf.N)"),
]

_MIL_EKI = re.compile(r"[MmNn][Il1|!][Ll1|I]\.?$")
_SAYI = re.compile(r"^[+\-−–]?\d{1,4}$")


@dataclass
class Okuma:
    panel: bool = False                 # SPA paneli görünüyor mu
    yukselis: int | None = None         # beyaz/sarı ELEVATION (namlunun şu anki MIL değeri)
    kirmizi: int | None = None          # kırmızı MIL (eğim)
    silah: str = ""                     # PRIMARY altındaki silah adı
    tank: str | None = None             # silah adından bulunan tank anahtarı
    ham: list = field(default_factory=list)


def sayi_coz(metin: str) -> int | None:
    """'0MIL', 'OMIL', '+60MlL', '-12MIL' -> sayı. Sayı değilse None."""
    t = metin.strip().replace(" ", "")
    t = _MIL_EKI.sub("", t)
    t = t.translate(str.maketrans({"O": "0", "o": "0", "D": "0", "l": "1", "I": "1", "|": "1", "S": "5"}))
    if not _SAYI.match(t):
        return None
    return int(t.replace("−", "-").replace("–", "-"))


def tank_bul(silah: str) -> str | None:
    s = silah.upper().replace(" ", "")
    for anahtarlar, tank in SILAH_ANAHTARLARI:
        if any(a in s for a in anahtarlar):
            return tank
    return None


def _kirmizi_mi(resim: np.ndarray, x: int, y: int, g: int, y2: int) -> bool:
    """Kelimenin kutusundaki parlak piksellerin ortalaması kırmızı mı?"""
    parca = resim[max(0, y):y2, max(0, x):x + g, :3].astype(np.int32)
    if parca.size == 0:
        return False
    parlak = parca[parca.max(axis=2) > 120]
    if len(parlak) < 3:
        return False
    r, gr, b = parlak.mean(axis=0)
    return r > 120 and r - gr > 35 and r - b > 35       # örnekte kırmızı (158,102,103), sarı (204,194,144)


class EkranOkuyucu:
    def __init__(self, monitor_no: int = 1):
        self.monitor_no = monitor_no
        self._mss = None
        self.motor = (OcrEngine.try_create_from_language(Language("en-US"))
                      or OcrEngine.try_create_from_user_profile_languages())
        if self.motor is None:
            raise RuntimeError("Windows yazı tanıma motoru açılamadı (dil paketi yok)")

    def _yakala(self) -> np.ndarray:
        if self._mss is None:                     # mss iş parçacığına bağlı: kullanan iş parçacığında aç
            self._mss = mss.MSS()
        mon = self._mss.monitors[min(self.monitor_no, len(self._mss.monitors) - 1)]
        sol = mon["left"] + int(mon["width"] * (1 - BOLGE_SAG))
        ust = mon["top"] + int(mon["height"] * (1 - BOLGE_ALT))
        kare = self._mss.grab({"left": sol, "top": ust, "width": mon["left"] + mon["width"] - sol,
                               "height": mon["top"] + mon["height"] - ust})
        return np.asarray(kare)[:, :, [2, 1, 0, 3]]   # BGRA -> RGBA

    def oku(self, resim: np.ndarray | None = None) -> Okuma:
        """resim verilmezse ekrandan yakalar (RGBA, sağ alt bölge)."""
        if resim is None:
            resim = self._yakala()
        olcek = 2 if resim.shape[0] < 500 else 1     # 1080p altı ekranda yazı küçük: büyüterek oku
        im = Image.fromarray(np.ascontiguousarray(resim[:, :, :4]), "RGBA")
        if olcek != 1:
            im = im.resize((im.width * olcek, im.height * olcek), Image.LANCZOS)
        satirlar = asyncio.run(self._tani(im))
        return self._coz(satirlar, resim, olcek)

    async def _tani(self, im: Image.Image):
        yazici = DataWriter()
        yazici.write_bytes(im.tobytes())
        bmp = SoftwareBitmap.create_copy_from_buffer(yazici.detach_buffer(), BitmapPixelFormat.RGBA8,
                                                     im.width, im.height)
        sonuc = await self.motor.recognize_async(bmp)
        return [[(k.text, k.bounding_rect.x, k.bounding_rect.y, k.bounding_rect.width, k.bounding_rect.height)
                 for k in s.words] for s in sonuc.lines]

    @staticmethod
    def _coz(satirlar, resim: np.ndarray, olcek: int) -> Okuma:
        o = Okuma(ham=[" ".join(k[0] for k in s) for s in satirlar])
        kelimeler = [k for s in satirlar for k in s]
        # ELEVATION satırı
        elev = next((k for k in kelimeler if k[0].upper().replace("0", "O").startswith("ELEVAT")), None)
        if elev:
            o.panel = True
            orta = elev[2] + elev[4] / 2
            sagdakiler = sorted((k for k in kelimeler if k[1] > elev[1] + elev[3] - 2
                                 and abs(k[2] + k[4] / 2 - orta) < elev[4] * 0.8), key=lambda k: k[1])
            for metin, x, y, g, yk in sagdakiler:
                deger = sayi_coz(metin)
                if deger is None:
                    continue
                kirmizi = _kirmizi_mi(resim, int(x / olcek), int(y / olcek), int(g / olcek) + 1,
                                      int((y + yk) / olcek) + 1)
                if kirmizi and o.kirmizi is None:
                    o.kirmizi = deger
                elif not kirmizi and o.yukselis is None:
                    o.yukselis = deger
        # PRIMARY'nin hemen altındaki kelimeler = ana silahın adı (konumla; OCR satır sırası güvenilmez)
        prim = next((k for k in kelimeler if k[0].upper().startswith("PRIMAR")), None)
        if prim:
            alt = sorted((k for k in kelimeler if prim[2] + prim[4] * 0.6 < k[2] < prim[2] + prim[4] * 3
                          and k[1] > prim[1] - prim[4] and k[1] < prim[1] + prim[3] * 4), key=lambda k: k[1])
            o.silah = " ".join(k[0] for k in alt if k[0].upper() != "EMPTY")
            o.tank = tank_bul(o.silah)
        return o
