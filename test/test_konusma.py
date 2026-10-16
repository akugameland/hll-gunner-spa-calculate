"""Whisper + sayı çözümü: python -X utf8 test/test_konusma.py <wav klasörü> [tr|en] [whisper_klasoru]
(klasörde 0.wav, 1.wav... 16 kHz mono ve metinler.txt)"""
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import konusma  # noqa: E402
import sayilar  # noqa: E402

klasor = Path(sys.argv[1])
dil = sys.argv[2] if len(sys.argv) > 2 else "tr"
ek = sys.argv[3] if len(sys.argv) > 3 else ""
metinler = (klasor / "metinler.txt").read_text(encoding="utf-8").splitlines()
t = time.perf_counter()
tanima = konusma.Tanima(dil, ek)
print(f"model: {tanima.cihaz} ({time.perf_counter() - t:.1f} sn)")
for i, beklenen in enumerate(metinler):
    with wave.open(str(klasor / f"{i}.wav")) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
    t = time.perf_counter()
    yazi = tanima.yaziya(pcm)
    print(f"{beklenen!r:40} -> {yazi!r:30} -> {sayilar.coz(yazi, dil)}  ({time.perf_counter() - t:.2f} sn)"
          f"  sayı(beklenen)={sayilar.coz(beklenen, dil)}")
