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


DURUMLAR = [("çok kısa", np.zeros(1600, np.float32)), ("sessiz", np.zeros(16000, np.float32)),
            ("gürültü", np.random.default_rng(1).normal(0, 0.003, 16000).astype(np.float32))]


def adim2(i=0):                                  # ses kontrolü ayrı iş parçacığında: sonucu bekle
    if i < len(DURUMLAR):
        ad, pcm = DURUMLAR[i]
        app.mikrofon.bitir = lambda pcm=pcm: pcm
        app._tus_isle(True)
        app._tus_isle(False)
        app.kok.after(1500, lambda: (sonuclar.append((ad, altyazi())), adim2(i + 1)))
        return
    uygulama.yetki.tuslar_engelli_mi = lambda: True
    app._engel_zamani = 0
    sonuclar.append(("oyun yönetici", altyazi()))
    sonuclar.append(("kutu", app.okunan.cget("text").splitlines()[-1]))
    app._mikrofon_bul()                          # gerçek mikrofonlar, 3 sn
    app.kok.after(4500, bitir)


def bitir():
    sonuclar.append(("mikrofonu bul", [app.duyulan[0], app.bul_dugme.cget("text"), app.mik_kutu.get()]))
    for ad, satir in sonuclar:
        print(f"[{ad}] {satir}")
    app.kapat()


app.kok.after(100, adim1)
app.calis()
