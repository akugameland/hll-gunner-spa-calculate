"""Bas-konuş hiçbir durumda sessiz kalmamalı: hazır değil / çok kısa / sessiz / oyun yönetici.
python -X utf8 test/test_bas_konus.py"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uygulama  # noqa: E402

app = uygulama.Uygulama()
app._kaydet = lambda: None
sonuclar = []


def altyazi():
    app._goster()
    return [x[0] for x in app.altyazi.satirlar]


def adim1():                                     # model yüklenmeden basıldı
    app.mikrofon, app.tanima = None, None
    app._tus_isle(True)
    sonuclar.append(("hazır değil", altyazi()))
    app.kok.after(200, bekle)


def bekle():                                     # ses gerçekten hazır olana kadar bekle
    if app.mikrofon and app.tanima:
        adim2()
    else:
        app.kok.after(500, bekle)


def adim2():
    for ad, pcm in (("çok kısa", np.zeros(1600, np.float32)), ("sessiz", np.zeros(16000, np.float32))):
        app.mikrofon.bitir = lambda pcm=pcm: pcm
        app._tus_isle(True)
        app._tus_isle(False)
        sonuclar.append((ad, altyazi()))
    uygulama.yetki.tuslar_engelli_mi = lambda: True
    app._engel_zamani = 0
    sonuclar.append(("oyun yönetici", altyazi()))
    sonuclar.append(("kutu", app.okunan.cget("text").splitlines()[-1]))
    for ad, satir in sonuclar:
        print(f"[{ad}] {satir}")
    app.kapat()


app.kok.after(100, adim1)
app.calis()
