"""Uçtan uca: örnek oyun görüntüsü tam ekran açılır, program ekrandan okur, kayıtlı ses bas-konuş gibi verilir.
python -X utf8 test/e2e.py <oyun_görüntüsü> <wav> <çıktı_png> [tr|en]"""
import sys
import tkinter as tk
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uygulama  # noqa: E402  (konusma'yı winrt'den önce yükler)
import mss  # noqa: E402
from PIL import Image, ImageTk  # noqa: E402

goruntu, wav, cikti = sys.argv[1:4]
app = uygulama.Uygulama()
app._kaydet = lambda: None                      # test kullanıcının ayarlarını değiştirmesin
if len(sys.argv) > 4:
    app.dil_kutu.set(uygulama.DIL_ADLARI[sys.argv[4]])
    app._dil_secildi()
sahne = tk.Toplevel(app.kok)
sahne.overrideredirect(True)
with mss.MSS() as m:
    mon = m.monitors[1]
sahne.geometry(f"{mon['width']}x{mon['height']}+{mon['left']}+{mon['top']}")
foto = ImageTk.PhotoImage(Image.open(goruntu).convert("RGB").resize((mon["width"], mon["height"])))
tk.Label(sahne, image=foto, bd=0).pack()
sahne.lift()   # en-önde değil: altyazı kendi pencerelerini örtücü saymaz, gerçek oyun ayrı programdır
with wave.open(wav) as w:
    pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0


def bekle_hazir():
    if app.tanima and app.mikrofon:
        app.mikrofon.bitir = lambda: pcm                 # mikrofon yerine kayıtlı ses
        app._tus(True)
        app.kok.after(400, lambda: app._tus(False))
        app.kok.after(5000, son)
    else:
        print("bekliyor:", app.durum.cget("text"), flush=True)
        app.kok.after(2000, bekle_hazir)


def son():
    try:
        with mss.MSS() as m:
            k = m.grab(m.monitors[1])
            Image.frombytes("RGB", k.size, k.rgb).save(cikti)
        print("hedef:", app.hedef, "| okuma:", app.okuma.yukselis, app.okuma.kirmizi, app.okuma.tank)
        print("altyazı:", [x[0] for x in app.altyazi.satirlar])
        print("geçmiş:", app.gecmis.get(0, "end"))
        print("durum:", app.durum.cget("text"))
        print("okunan:", " | ".join(app.okunan.cget("text").splitlines()))
    finally:
        app.kapat()


app.kok.after(500, bekle_hazir)
app.calis()
