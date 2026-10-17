"""Kısık mikrofon kabul edilmeli, sessizlik/gürültü reddedilmeli.
python -X utf8 test/test_kisik_ses.py <wav klasörü> [whisper_klasoru]"""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import konusma  # noqa: E402
import sayilar  # noqa: E402

klasor = Path(sys.argv[1])
tanima = konusma.Tanima("tr", sys.argv[2] if len(sys.argv) > 2 else "")
with wave.open(str(klasor / "0.wav")) as w:                     # "Dört yüz elli metre."
    ses = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
rng = np.random.default_rng(1)
durumlar = [("normal", ses, True)]
for kat in (0.1, 0.03, 0.01, 0.005):
    durumlar.append((f"kısık x{kat}", ses * kat + rng.normal(0, 0.0002, len(ses)).astype(np.float32), True))
durumlar += [("sıfır", np.zeros(32000, np.float32), False),
             ("gürültü", rng.normal(0, 0.003, 32000).astype(np.float32), False),
             ("uğultu", (0.01 * np.sin(np.arange(32000) * 2 * np.pi * 50 / 16000)).astype(np.float32), False),
             ("çok kısa", ses[:3000], False)]
hata = 0
for ad, pcm, beklenen in durumlar:
    hazir, sebep = konusma.hazirla(pcm)
    metin = tanima.yaziya(hazir) if hazir is not None else ""
    sonuc = sayilar.coz(metin, "tr") if metin else None
    dogru = (sonuc == (450, 0)) if beklenen else hazir is None
    hata += not dogru
    print(f"{'OK  ' if dogru else 'HATA'} {ad:12} seviye={konusma.seviye(pcm):.4f} sebep={sebep or '-':7} {metin!r} -> {sonuc}")
sys.exit(1 if hata else 0)
